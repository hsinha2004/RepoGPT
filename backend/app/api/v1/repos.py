"""
Repository management API endpoints (§12).
Supports creating repos from GitHub URL, ZIP upload, listing, details, settings, and members.
"""

import os
import shutil
import uuid
from typing import Any

import structlog
from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status

from app.core.config import get_settings
from app.core.deps import get_current_user
from app.core.errors import ForbiddenError, NotFoundError, ValidationFailedError
from app.core.security import decrypt_secret
from app.db.repositories.files import FileRepository
from app.db.repositories.jobs import JobRepository
from app.db.repositories.members import RepoMemberRepository
from app.db.repositories.repos import RepositoryRepository
from app.db.repositories.users import UserRepository
from app.jobs.tasks import ingest_repository_task
from app.schemas.repos import (
    RepoCreateGitHubRequest,
    RepoListResponse,
    RepoMemberAddRequest,
    RepoMemberResponse,
    RepoResponse,
    RepoUpdateSettingsRequest,
)
from app.services.ingestion.archive import is_valid_zip_magic
from app.services.ingestion.github_fetcher import parse_github_url

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/repos", tags=["repos"])


def get_repo_repository() -> RepositoryRepository:
    return RepositoryRepository()


def get_member_repository() -> RepoMemberRepository:
    return RepoMemberRepository()


def get_job_repository() -> JobRepository:
    return JobRepository()


def get_file_repository() -> FileRepository:
    return FileRepository()


def get_user_repository() -> UserRepository:
    return UserRepository()


def _format_repo_response(doc: dict[str, Any]) -> RepoResponse:
    return RepoResponse(
        id=str(doc["_id"]),
        owner_id=str(doc["owner_id"]),
        source=doc["source"],
        display_name=doc["display_name"],
        description=doc.get("description", ""),
        commit_sha=doc.get("commit_sha"),
        status=doc.get("status", "queued"),
        status_message=doc.get("status_message", ""),
        stats=doc.get("stats", {}),
        settings=doc.get("settings", {}),
        last_indexed_at=doc.get("last_indexed_at"),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


@router.post(
    "",
    response_model=dict[str, Any],
    status_code=status.HTTP_201_CREATED,
    summary="Add repository from GitHub",
)
async def create_from_github(
    payload: RepoCreateGitHubRequest,
    user: dict[str, Any] = Depends(get_current_user),
    repo_repo: RepositoryRepository = Depends(get_repo_repository),
    member_repo: RepoMemberRepository = Depends(get_member_repository),
    job_repo: JobRepository = Depends(get_job_repository),
    user_repo: UserRepository = Depends(get_user_repository),
) -> dict[str, Any]:
    """Validates GitHub URL and initiates asynchronous repository ingestion job."""
    owner, repo_name, ref = parse_github_url(payload.url)
    effective_ref = payload.ref or ref

    source = {
        "type": "github",
        "url": payload.url,
        "owner": owner,
        "name": repo_name,
        "ref": effective_ref,
        "default_branch": None,
        "is_private": False,
        "upload_filename": None,
    }

    user_id = str(user["_id"])
    repo_doc = await repo_repo.create_repository(
        owner_id=user_id,
        source=source,
        display_name=f"{owner}/{repo_name}",
        description="",
    )
    repo_id = str(repo_doc["_id"])

    # Add user as owner in repo_members
    await member_repo.add_member(repo_id=repo_id, user_id=user_id, role="owner", added_by=user_id)

    # Resolve PAT if user has one configured
    user_full = await user_repo.get_by_id(user_id)
    pat = None
    if user_full and user_full.get("github_pat_encrypted"):
        try:
            pat = decrypt_secret(user_full["github_pat_encrypted"])
        except Exception:
            pass

    # Create job
    job_doc = await job_repo.create_job(job_type="ingest", repo_id=repo_id, user_id=user_id)
    job_id = str(job_doc["_id"])

    # Dispatch Celery task
    try:
        task_res = ingest_repository_task.delay(
            job_id=job_id, repo_id=repo_id, archive_path=None, github_pat=pat
        )
        await job_repo.mark_running(job_id, celery_task_id=task_res.id)
    except Exception as e:
        logger.warning("celery_dispatch_failed_running_inline_or_queued", error=str(e))

    return {
        "repository": _format_repo_response(repo_doc),
        "job_id": job_id,
    }


@router.post(
    "/upload",
    response_model=dict[str, Any],
    status_code=status.HTTP_201_CREATED,
    summary="Upload ZIP repository",
)
async def upload_repository_archive(
    file: UploadFile = File(...),
    display_name: str | None = Form(None),
    user: dict[str, Any] = Depends(get_current_user),
    repo_repo: RepositoryRepository = Depends(get_repo_repository),
    member_repo: RepoMemberRepository = Depends(get_member_repository),
    job_repo: JobRepository = Depends(get_job_repository),
) -> dict[str, Any]:
    """Uploads a ZIP archive, validates magic bytes, and begins background ingestion."""
    settings = get_settings()
    filename = file.filename or "repository.zip"
    repo_name = display_name or filename.replace(".zip", "")

    # Save to temp uploads directory
    uploads_dir = os.path.join(settings.DATA_DIR, "uploads", "tmp")
    os.makedirs(uploads_dir, exist_ok=True)
    temp_file_path = os.path.join(uploads_dir, f"upload_{uuid.uuid4().hex}.zip")

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    total_bytes = 0

    with open(temp_file_path, "wb") as buffer:
        while chunk := await file.read(65536):
            total_bytes += len(chunk)
            if total_bytes > max_bytes:
                buffer.close()
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
                raise ValidationFailedError(
                    f"Upload size exceeded maximum limit of {settings.MAX_UPLOAD_SIZE_MB} MB."
                )
            buffer.write(chunk)

    # Magic byte validation
    if not is_valid_zip_magic(temp_file_path):
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        raise ValidationFailedError(
            "Uploaded file is not a valid ZIP archive (magic bytes mismatch)."
        )

    user_id = str(user["_id"])
    source = {
        "type": "upload",
        "url": None,
        "owner": user.get("name", "User"),
        "name": repo_name,
        "ref": "main",
        "default_branch": "main",
        "is_private": True,
        "upload_filename": filename,
    }

    repo_doc = await repo_repo.create_repository(
        owner_id=user_id,
        source=source,
        display_name=repo_name,
        description="Uploaded from ZIP archive",
    )
    repo_id = str(repo_doc["_id"])

    await member_repo.add_member(repo_id=repo_id, user_id=user_id, role="owner", added_by=user_id)

    job_doc = await job_repo.create_job(job_type="ingest", repo_id=repo_id, user_id=user_id)
    job_id = str(job_doc["_id"])

    try:
        task_res = ingest_repository_task.delay(
            job_id=job_id,
            repo_id=repo_id,
            archive_path=temp_file_path,
            github_pat=None,
        )
        await job_repo.mark_running(job_id, celery_task_id=task_res.id)
    except Exception as e:
        logger.warning("celery_dispatch_failed_running_inline_or_queued", error=str(e))

    return {
        "repository": _format_repo_response(repo_doc),
        "job_id": job_id,
    }


@router.get("", response_model=RepoListResponse, summary="List accessible repositories")
async def list_repositories(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user: dict[str, Any] = Depends(get_current_user),
    repo_repo: RepositoryRepository = Depends(get_repo_repository),
    member_repo: RepoMemberRepository = Depends(get_member_repository),
) -> RepoListResponse:
    """Lists all repositories owned by or shared with the authenticated user."""
    user_id = str(user["_id"])
    member_repo_ids = await member_repo.get_user_repo_ids(user_id)
    repos, total = await repo_repo.list_for_user(
        user_id=user_id,
        accessible_repo_ids=member_repo_ids,
        skip=skip,
        limit=limit,
    )
    items = [_format_repo_response(r) for r in repos]
    return RepoListResponse(items=items, total=total)


@router.get("/{repo_id}", response_model=RepoResponse, summary="Get repository details")
async def get_repository(
    repo_id: str,
    user: dict[str, Any] = Depends(get_current_user),
    repo_repo: RepositoryRepository = Depends(get_repo_repository),
    member_repo: RepoMemberRepository = Depends(get_member_repository),
) -> RepoResponse:
    """Fetches details for a specific repository."""
    user_id = str(user["_id"])
    repo_doc = await repo_repo.get_by_id(repo_id)
    if not repo_doc:
        raise NotFoundError(f"Repository {repo_id} not found.")

    if repo_doc["owner_id"] != user_id:
        membership = await member_repo.get_member(repo_id, user_id)
        if not membership and user.get("role") != "admin":
            raise ForbiddenError("Access forbidden to this repository.")

    return _format_repo_response(repo_doc)


@router.patch("/{repo_id}", response_model=RepoResponse, summary="Update repository settings")
async def update_repository_settings(
    repo_id: str,
    payload: RepoUpdateSettingsRequest,
    user: dict[str, Any] = Depends(get_current_user),
    repo_repo: RepositoryRepository = Depends(get_repo_repository),
    member_repo: RepoMemberRepository = Depends(get_member_repository),
) -> RepoResponse:
    """Updates settings for a repository (requires owner or editor role)."""
    user_id = str(user["_id"])
    repo_doc = await repo_repo.get_by_id(repo_id)
    if not repo_doc:
        raise NotFoundError(f"Repository {repo_id} not found.")

    if repo_doc["owner_id"] != user_id:
        membership = await member_repo.get_member(repo_id, user_id)
        if (not membership or membership.get("role") == "viewer") and user.get("role") != "admin":
            raise ForbiddenError("Editor or owner permissions required to modify settings.")

    current_settings = repo_doc.get("settings", {})
    if payload.auto_review is not None:
        current_settings["auto_review"] = payload.auto_review
    if payload.extra_ignore_patterns is not None:
        current_settings["extra_ignore_patterns"] = payload.extra_ignore_patterns

    await repo_repo.update_settings(repo_id, current_settings)
    updated = await repo_repo.get_by_id(repo_id)
    return _format_repo_response(updated or repo_doc)


@router.delete("/{repo_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete repository")
async def delete_repository(
    repo_id: str,
    user: dict[str, Any] = Depends(get_current_user),
    repo_repo: RepositoryRepository = Depends(get_repo_repository),
    member_repo: RepoMemberRepository = Depends(get_member_repository),
    file_repo: FileRepository = Depends(get_file_repository),
) -> None:
    """Permanently deletes repository, member records, file indexes, and snapshots on disk."""
    user_id = str(user["_id"])
    repo_doc = await repo_repo.get_by_id(repo_id)
    if not repo_doc:
        raise NotFoundError(f"Repository {repo_id} not found.")

    if repo_doc["owner_id"] != user_id and user.get("role") != "admin":
        raise ForbiddenError("Only repository owner or admin can delete this repository.")

    settings = get_settings()

    # 1. Delete Mongo records
    await repo_repo.delete_repository(repo_id)
    await member_repo.delete_all_for_repo(repo_id)
    await file_repo.delete_for_repo(repo_id)

    # 2. Delete snapshot files on disk
    snapshot_path = os.path.join(settings.DATA_DIR, "snapshots", repo_id)
    if os.path.exists(snapshot_path):
        try:
            shutil.rmtree(snapshot_path)
        except Exception as e:
            logger.warning("cleanup_snapshot_failed", path=snapshot_path, error=str(e))

    return None


@router.get(
    "/{repo_id}/files", response_model=list[dict[str, Any]], summary="List repository files"
)
async def list_repo_files(
    repo_id: str,
    kind: str | None = Query(
        None, description="Filter by kind: 'code' | 'doc' | 'config' | 'test'"
    ),
    language: str | None = Query(None, description="Filter by language"),
    user: dict[str, Any] = Depends(get_current_user),
    repo_repo: RepositoryRepository = Depends(get_repo_repository),
    member_repo: RepoMemberRepository = Depends(get_member_repository),
    file_repo: FileRepository = Depends(get_file_repository),
) -> list[dict[str, Any]]:
    """Lists indexed files within the repository."""
    user_id = str(user["_id"])
    repo_doc = await repo_repo.get_by_id(repo_id)
    if not repo_doc:
        raise NotFoundError(f"Repository {repo_id} not found.")

    if repo_doc["owner_id"] != user_id:
        membership = await member_repo.get_member(repo_id, user_id)
        if not membership and user.get("role") != "admin":
            raise ForbiddenError("Access forbidden to this repository.")

    files = await file_repo.list_files(repo_id=repo_id, kind=kind, language=language)
    for f in files:
        f["id"] = str(f["_id"])
        del f["_id"]
    return files


@router.get(
    "/{repo_id}/members", response_model=list[RepoMemberResponse], summary="List repository members"
)
async def list_repo_members(
    repo_id: str,
    user: dict[str, Any] = Depends(get_current_user),
    repo_repo: RepositoryRepository = Depends(get_repo_repository),
    member_repo: RepoMemberRepository = Depends(get_member_repository),
    user_repo: UserRepository = Depends(get_user_repository),
) -> list[RepoMemberResponse]:
    """Lists all members of the repository."""
    user_id = str(user["_id"])
    repo_doc = await repo_repo.get_by_id(repo_id)
    if not repo_doc:
        raise NotFoundError(f"Repository {repo_id} not found.")

    if repo_doc["owner_id"] != user_id:
        membership = await member_repo.get_member(repo_id, user_id)
        if not membership and user.get("role") != "admin":
            raise ForbiddenError("Access forbidden to this repository.")

    members = await member_repo.list_members(repo_id)
    result = []
    for m in members:
        user_info = await user_repo.get_by_id(m["user_id"])
        email = user_info.get("email") if user_info else None
        result.append(
            RepoMemberResponse(
                repo_id=m["repo_id"],
                user_id=m["user_id"],
                email=email,
                role=m["role"],
                added_by=m["added_by"],
                created_at=m["created_at"],
            )
        )
    return result


@router.post(
    "/{repo_id}/members",
    response_model=RepoMemberResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add repository member",
)
async def add_repo_member(
    repo_id: str,
    payload: RepoMemberAddRequest,
    user: dict[str, Any] = Depends(get_current_user),
    repo_repo: RepositoryRepository = Depends(get_repo_repository),
    member_repo: RepoMemberRepository = Depends(get_member_repository),
    user_repo: UserRepository = Depends(get_user_repository),
) -> RepoMemberResponse:
    """Adds a member to the repository by email."""
    user_id = str(user["_id"])
    repo_doc = await repo_repo.get_by_id(repo_id)
    if not repo_doc:
        raise NotFoundError(f"Repository {repo_id} not found.")

    if repo_doc["owner_id"] != user_id and user.get("role") != "admin":
        raise ForbiddenError("Only the repository owner can manage members.")

    target_user = await user_repo.get_by_email(payload.email)
    if not target_user:
        raise NotFoundError(f"User with email '{payload.email}' not found.")

    target_uid = str(target_user["_id"])
    doc = await member_repo.add_member(
        repo_id=repo_id,
        user_id=target_uid,
        role=payload.role,
        added_by=user_id,
    )

    return RepoMemberResponse(
        repo_id=repo_id,
        user_id=target_uid,
        email=target_user["email"],
        role=doc["role"],
        added_by=doc["added_by"],
        created_at=doc["created_at"],
    )


@router.delete(
    "/{repo_id}/members/{target_user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove repository member",
)
async def remove_repo_member(
    repo_id: str,
    target_user_id: str,
    user: dict[str, Any] = Depends(get_current_user),
    repo_repo: RepositoryRepository = Depends(get_repo_repository),
    member_repo: RepoMemberRepository = Depends(get_member_repository),
) -> None:
    """Removes a member from the repository."""
    user_id = str(user["_id"])
    repo_doc = await repo_repo.get_by_id(repo_id)
    if not repo_doc:
        raise NotFoundError(f"Repository {repo_id} not found.")

    if repo_doc["owner_id"] != user_id and user.get("role") != "admin":
        raise ForbiddenError("Only the repository owner can remove members.")

    if repo_doc["owner_id"] == target_user_id:
        raise ValidationFailedError("Cannot remove repository owner.")

    await member_repo.remove_member(repo_id, target_user_id)
    return None

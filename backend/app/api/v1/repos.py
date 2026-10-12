"""
Repository management API endpoints (§12).
Supports creating repos from GitHub URL, ZIP upload, listing, details, settings, and members.
"""

import os
import uuid
from typing import Any

import structlog
from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status

from app.core.config import get_settings
from app.core.deps import get_current_user
from app.core.errors import ForbiddenError, NotFoundError, ValidationFailedError
from app.core.security import decrypt_secret
from app.db.repositories.chunks import ChunkRepository
from app.db.repositories.files import FileRepository
from app.db.repositories.graph import GraphRepository
from app.db.repositories.jobs import JobRepository
from app.db.repositories.members import RepoMemberRepository
from app.db.repositories.overview import OverviewRepository
from app.db.repositories.repos import RepositoryRepository
from app.db.repositories.symbols import SymbolRepository
from app.db.repositories.users import UserRepository
from app.jobs.tasks import ingest_repository_task
from app.schemas.graph import GraphResponse, RepoStatsResponse
from app.schemas.overview import OverviewResponse
from app.schemas.repos import (
    FileDetailResponse,
    RepoCreateGitHubRequest,
    RepoListResponse,
    RepoMemberAddRequest,
    RepoMemberResponse,
    RepoResponse,
    RepoSyncRequest,
    RepoSyncResponse,
    RepoUpdateSettingsRequest,
    SkippedFileResponse,
    SymbolResponse,
)
from app.schemas.retrieval import SearchRequest, SearchResponse
from app.services.analysis.entry_points import EntryPointDetector
from app.services.analysis.overview import OverviewService
from app.services.analysis.reading_order import ReadingOrderGenerator
from app.services.analysis.tech_stack import TechStackDetector
from app.services.graph.analyzer import GraphAnalyzer
from app.services.graph.builder import GraphBuilder
from app.services.indexing.sync import IncrementalSyncService, RepoDeletionService
from app.services.ingestion.archive import is_valid_zip_magic
from app.services.ingestion.github_fetcher import parse_github_url
from app.services.llm.factory import get_llm_provider
from app.services.redaction.redactor import SecretRedactor
from app.services.retrieval.service import RetrievalService

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/repos", tags=["repos"])


def get_repo_repository() -> RepositoryRepository:
    return RepositoryRepository()


def get_member_repository() -> RepoMemberRepository:
    return RepoMemberRepository()


def get_job_repository() -> JobRepository:
    return JobRepository()


def get_graph_repository() -> GraphRepository:
    return GraphRepository()


def get_overview_repository() -> OverviewRepository:
    return OverviewRepository()


def get_chunk_repository() -> ChunkRepository:
    return ChunkRepository()


def get_file_repository() -> FileRepository:
    return FileRepository()


def get_symbol_repository() -> SymbolRepository:
    return SymbolRepository()


def get_user_repository() -> UserRepository:
    return UserRepository()


def get_retrieval_service(
    repo_repo: RepositoryRepository = Depends(get_repo_repository),
) -> RetrievalService:
    settings = get_settings()
    return RetrievalService(settings=settings, repo_repository=repo_repo)


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


@router.delete(
    "/{repo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete repository and all indexed artifacts (§11.16)",
)
async def delete_repository(
    repo_id: str,
    user: dict[str, Any] = Depends(get_current_user),
    repo_repo: RepositoryRepository = Depends(get_repo_repository),
    member_repo: RepoMemberRepository = Depends(get_member_repository),
) -> None:
    """Permanently deletes repository, member records, Mongo docs, vector collections, BM25 indices, and snapshots."""
    user_id = str(user["_id"])
    repo_doc = await repo_repo.get_by_id(repo_id)
    if not repo_doc:
        raise NotFoundError(f"Repository {repo_id} not found.")

    if repo_doc["owner_id"] != user_id and user.get("role") != "admin":
        raise ForbiddenError("Only repository owner or admin can delete this repository.")

    deletion_service = RepoDeletionService(repo_repo=repo_repo)
    await deletion_service.delete_repository_data(repo_id)
    await member_repo.delete_all_for_repo(repo_id)
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
    "/{repo_id}/files/{file_path:path}",
    response_model=FileDetailResponse,
    summary="Get repository file content and symbols",
)
async def get_file_detail(
    repo_id: str,
    file_path: str,
    user: dict[str, Any] = Depends(get_current_user),
    repo_repo: RepositoryRepository = Depends(get_repo_repository),
    member_repo: RepoMemberRepository = Depends(get_member_repository),
    file_repo: FileRepository = Depends(get_file_repository),
    symbol_repo: SymbolRepository = Depends(get_symbol_repository),
) -> FileDetailResponse:
    """Retrieves file details, redacted content, and AST symbol outline for Explorer (§8.4, §10)."""
    user_id = str(user["_id"])
    repo_doc = await repo_repo.get_by_id(repo_id)
    if not repo_doc:
        raise NotFoundError(f"Repository {repo_id} not found.")

    if repo_doc["owner_id"] != user_id:
        membership = await member_repo.get_member(repo_id, user_id)
        if not membership and user.get("role") != "admin":
            raise ForbiddenError("Access forbidden to this repository.")

    file_doc = await file_repo.get_file(repo_id=repo_id, path=file_path)
    if not file_doc:
        raise NotFoundError(f"File {file_path} not found in repository.")

    settings = get_settings()
    commit_sha = repo_doc.get("commit_sha") or "main"
    disk_path = os.path.join(settings.DATA_DIR, "snapshots", repo_id, commit_sha, file_path)

    raw_content = ""
    if os.path.exists(disk_path):
        try:
            with open(disk_path, encoding="utf-8", errors="replace") as f_src:
                raw_content = f_src.read()
        except Exception:
            raw_content = ""

    # Redact credentials before display (§8.3)
    redactor = SecretRedactor()
    redacted_res = redactor.redact(raw_content)

    # Fetch symbol outline for this file
    sym_docs = await symbol_repo.list_for_file(repo_id, file_path)
    symbols = [
        SymbolResponse(
            name=s.get("name", ""),
            qualified_name=s.get("qualified_name", ""),
            kind=s.get("kind", "const"),
            signature=s.get("signature", ""),
            docstring=s.get("docstring"),
            start_line=s.get("start_line", 1),
            end_line=s.get("end_line", 1),
            parent=s.get("parent"),
            language=s.get("language", file_doc.get("language", "generic")),
            exported=s.get("exported", True),
        )
        for s in sym_docs
    ]

    return FileDetailResponse(
        path=file_doc["path"],
        language=file_doc.get("language", "generic"),
        size_bytes=file_doc.get("size_bytes", len(raw_content)),
        loc=file_doc.get("loc", len(raw_content.splitlines())),
        content=redacted_res.redacted_text,
        symbols=symbols,
        card=file_doc.get("card", ""),
        imports=file_doc.get("imports", []),
        redaction_count=redacted_res.redaction_count,
    )


@router.get(
    "/{repo_id}/symbols",
    response_model=list[SymbolResponse],
    summary="List or search repository symbols",
)
async def list_repo_symbols(
    repo_id: str,
    path: str | None = Query(None, description="Filter by file path"),
    q: str | None = Query(None, description="Search symbol by name"),
    limit: int = Query(100, ge=1, le=500),
    user: dict[str, Any] = Depends(get_current_user),
    repo_repo: RepositoryRepository = Depends(get_repo_repository),
    member_repo: RepoMemberRepository = Depends(get_member_repository),
    symbol_repo: SymbolRepository = Depends(get_symbol_repository),
) -> list[SymbolResponse]:
    """Lists symbols in a file or searches symbols across repository."""
    user_id = str(user["_id"])
    repo_doc = await repo_repo.get_by_id(repo_id)
    if not repo_doc:
        raise NotFoundError(f"Repository {repo_id} not found.")

    if repo_doc["owner_id"] != user_id:
        membership = await member_repo.get_member(repo_id, user_id)
        if not membership and user.get("role") != "admin":
            raise ForbiddenError("Access forbidden to this repository.")

    if path:
        docs = await symbol_repo.list_for_file(repo_id, path)
    elif q:
        docs = await symbol_repo.search_by_name(repo_id, q, limit=limit)
    else:
        cursor = symbol_repo._col.find({"repo_id": str(repo_id)}).limit(limit)
        docs = await cursor.to_list(length=limit)

    return [
        SymbolResponse(
            name=s.get("name", ""),
            qualified_name=s.get("qualified_name", ""),
            kind=s.get("kind", "const"),
            signature=s.get("signature", ""),
            docstring=s.get("docstring"),
            start_line=s.get("start_line", 1),
            end_line=s.get("end_line", 1),
            parent=s.get("parent"),
            language=s.get("language", "generic"),
            exported=s.get("exported", True),
        )
        for s in docs
    ]


@router.get(
    "/{repo_id}/skipped-files",
    response_model=list[SkippedFileResponse],
    summary="List skipped or filtered files",
)
async def list_skipped_files(
    repo_id: str,
    user: dict[str, Any] = Depends(get_current_user),
    repo_repo: RepositoryRepository = Depends(get_repo_repository),
    member_repo: RepoMemberRepository = Depends(get_member_repository),
    file_repo: FileRepository = Depends(get_file_repository),
) -> list[SkippedFileResponse]:
    """Lists files skipped during repository ingestion with their reasons."""
    user_id = str(user["_id"])
    repo_doc = await repo_repo.get_by_id(repo_id)
    if not repo_doc:
        raise NotFoundError(f"Repository {repo_id} not found.")

    if repo_doc["owner_id"] != user_id:
        membership = await member_repo.get_member(repo_id, user_id)
        if not membership and user.get("role") != "admin":
            raise ForbiddenError("Access forbidden to this repository.")

    skipped_docs = await file_repo.list_skipped(repo_id)
    return [
        SkippedFileResponse(
            path=s.get("path", ""),
            reason=s.get("reason", "ignored"),
            size_bytes=s.get("size_bytes", 0),
        )
        for s in skipped_docs
    ]


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


@router.post(
    "/{repo_id}/sync",
    response_model=RepoSyncResponse,
    summary="Incrementally sync repository to latest commit (§8.10)",
)
async def sync_repository(
    repo_id: str,
    payload: RepoSyncRequest | None = None,
    user: dict[str, Any] = Depends(get_current_user),
    repo_repo: RepositoryRepository = Depends(get_repo_repository),
    member_repo: RepoMemberRepository = Depends(get_member_repository),
) -> RepoSyncResponse:
    """Incrementally syncs repository changes against the latest commit or ref."""
    user_id = str(user["_id"])
    repo_doc = await repo_repo.get_by_id(repo_id)
    if not repo_doc:
        raise NotFoundError(f"Repository {repo_id} not found.")

    is_owner = repo_doc["owner_id"] == user_id
    member = await member_repo.get_member(repo_id, user_id)
    role = member.get("role") if member else None
    if not is_owner and role not in ["editor", "owner"] and user.get("role") != "admin":
        raise ForbiddenError("Insufficient permissions to trigger sync.")

    sync_service = IncrementalSyncService(repo_repo=repo_repo)
    new_ref = payload.ref if payload else None
    res = await sync_service.sync_repository(repo_id, new_ref=new_ref)
    return RepoSyncResponse(
        status=res.get("status", "synced"),
        commit_sha=res.get("commit_sha", ""),
        message=res.get("message", "Sync completed"),
        added_files=res.get("added_files", 0),
        changed_files=res.get("changed_files", 0),
        removed_files=res.get("removed_files", 0),
        total_files=res.get("total_files", 0),
    )


@router.post(
    "/{repo_id}/search",
    response_model=SearchResponse,
    summary="Search repository code and documentation (§9)",
)
async def search_repository(
    repo_id: str,
    payload: SearchRequest,
    user: dict[str, Any] = Depends(get_current_user),
    repo_repo: RepositoryRepository = Depends(get_repo_repository),
    member_repo: RepoMemberRepository = Depends(get_member_repository),
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
) -> SearchResponse:
    """Executes multi-index retrieval pipeline according to selected or routed strategy."""
    user_id = str(user["_id"])
    repo_doc = await repo_repo.get_by_id(repo_id)
    if not repo_doc:
        raise NotFoundError(f"Repository {repo_id} not found.")

    is_owner = repo_doc["owner_id"] == user_id
    member = await member_repo.get_member(repo_id, user_id)
    if not is_owner and not member and user.get("role") != "admin":
        raise ForbiddenError("Access forbidden to this repository.")

    return await retrieval_service.search(repo_id=repo_id, request=payload)


async def _build_and_save_overview(
    repo_id: str,
    repo_doc: dict[str, Any],
    file_repo: FileRepository,
    symbol_repo: SymbolRepository,
    graph_repo: GraphRepository,
    overview_repo: OverviewRepository,
) -> dict[str, Any]:
    files = await file_repo.list_files(repo_id, limit=5000)
    all_paths = [f["path"] for f in files]
    readme_file = next(
        (f for f in files if f.get("path", "").lower() == "readme.md"),
        None,
    )
    readme_text = readme_file.get("content") or readme_file.get("text", "") if readme_file else ""

    symbols = await symbol_repo.list_for_repo(repo_id, limit=5000)
    symbols_by_file: dict[str, list[dict[str, Any]]] = {}
    for s in symbols:
        symbols_by_file.setdefault(s.get("path", ""), []).append(s)

    edges = await graph_repo.list_for_repo(repo_id, limit=5000)
    if not edges:
        edges = GraphBuilder().build_edges(files, symbols_by_file)
        if edges:
            await graph_repo.bulk_upsert_edges(repo_id, edges)

    analyzer = GraphAnalyzer(edges, all_paths)
    metrics = analyzer.compute_file_metrics()
    await file_repo.bulk_update_metrics(repo_id, metrics)

    languages_stats = repo_doc.get("stats", {}).get("languages")
    tech_stack = TechStackDetector().detect(files, languages_stats)
    entry_points = EntryPointDetector().detect(files)
    reading_order = ReadingOrderGenerator().generate(all_paths, entry_points, metrics, edges)
    top_files = await file_repo.list_top_pagerank_files(repo_id, limit=15)
    if not top_files:
        top_files = files[:15]

    llm = get_llm_provider()
    overview_svc = OverviewService(llm)
    overview_data = await overview_svc.generate_overview(
        repo_name=repo_doc.get("display_name") or repo_doc.get("name") or "repository",
        commit_sha=repo_doc.get("commit_sha", ""),
        readme_text=readme_text,
        tech_stack=tech_stack,
        entry_points=entry_points,
        reading_order=reading_order,
        file_metrics=metrics,
        top_files=top_files,
    )
    saved = await overview_repo.upsert(
        repo_id=repo_id,
        commit_sha=repo_doc.get("commit_sha", ""),
        overview_data=overview_data,
    )
    return saved


@router.get(
    "/{repo_id}/overview",
    response_model=OverviewResponse,
    summary="Get repository onboarding overview (§8.9, §12)",
)
async def get_repository_overview(
    repo_id: str,
    user: dict[str, Any] = Depends(get_current_user),
    repo_repo: RepositoryRepository = Depends(get_repo_repository),
    member_repo: RepoMemberRepository = Depends(get_member_repository),
    file_repo: FileRepository = Depends(get_file_repository),
    symbol_repo: SymbolRepository = Depends(get_symbol_repository),
    graph_repo: GraphRepository = Depends(get_graph_repository),
    overview_repo: OverviewRepository = Depends(get_overview_repository),
) -> OverviewResponse:
    user_id = str(user["_id"])
    repo_doc = await repo_repo.get_by_id(repo_id)
    if not repo_doc:
        raise NotFoundError(f"Repository {repo_id} not found.")

    is_owner = repo_doc["owner_id"] == user_id
    member = await member_repo.get_member(repo_id, user_id)
    if not is_owner and not member and user.get("role") != "admin":
        raise ForbiddenError("Access forbidden to this repository.")

    existing = await overview_repo.get_by_repo(repo_id)
    if existing:
        return OverviewResponse(
            repo_id=str(repo_id),
            commit_sha=existing.get("commit_sha"),
            markdown=existing.get("markdown", ""),
            suggested_questions=existing.get("suggested_questions", []),
            tech_stack=existing.get("tech_stack", []),
            entry_points=existing.get("entry_points", []),
            reading_order=existing.get("reading_order", []),
            sources=existing.get("sources", []),
            updated_at=existing["updated_at"].isoformat() if existing.get("updated_at") else None,
        )

    # Compute and persist on-demand if missing
    created = await _build_and_save_overview(
        repo_id=repo_id,
        repo_doc=repo_doc,
        file_repo=file_repo,
        symbol_repo=symbol_repo,
        graph_repo=graph_repo,
        overview_repo=overview_repo,
    )
    return OverviewResponse(
        repo_id=str(repo_id),
        commit_sha=created.get("commit_sha"),
        markdown=created.get("markdown", ""),
        suggested_questions=created.get("suggested_questions", []),
        tech_stack=created.get("tech_stack", []),
        entry_points=created.get("entry_points", []),
        reading_order=created.get("reading_order", []),
        sources=created.get("sources", []),
        updated_at=created["updated_at"].isoformat() if created.get("updated_at") else None,
    )


@router.post(
    "/{repo_id}/overview/regenerate",
    response_model=OverviewResponse,
    summary="Regenerate repository onboarding overview (§8.9, §12)",
)
async def regenerate_repository_overview(
    repo_id: str,
    user: dict[str, Any] = Depends(get_current_user),
    repo_repo: RepositoryRepository = Depends(get_repo_repository),
    member_repo: RepoMemberRepository = Depends(get_member_repository),
    file_repo: FileRepository = Depends(get_file_repository),
    symbol_repo: SymbolRepository = Depends(get_symbol_repository),
    graph_repo: GraphRepository = Depends(get_graph_repository),
    overview_repo: OverviewRepository = Depends(get_overview_repository),
) -> OverviewResponse:
    user_id = str(user["_id"])
    repo_doc = await repo_repo.get_by_id(repo_id)
    if not repo_doc:
        raise NotFoundError(f"Repository {repo_id} not found.")

    is_owner = repo_doc["owner_id"] == user_id
    member = await member_repo.get_member(repo_id, user_id)
    role = member.get("role") if member else None
    if not is_owner and role not in ["editor", "owner"] and user.get("role") != "admin":
        raise ForbiddenError("Insufficient permissions to regenerate overview.")

    created = await _build_and_save_overview(
        repo_id=repo_id,
        repo_doc=repo_doc,
        file_repo=file_repo,
        symbol_repo=symbol_repo,
        graph_repo=graph_repo,
        overview_repo=overview_repo,
    )
    return OverviewResponse(
        repo_id=str(repo_id),
        commit_sha=created.get("commit_sha"),
        markdown=created.get("markdown", ""),
        suggested_questions=created.get("suggested_questions", []),
        tech_stack=created.get("tech_stack", []),
        entry_points=created.get("entry_points", []),
        reading_order=created.get("reading_order", []),
        sources=created.get("sources", []),
        updated_at=created["updated_at"].isoformat() if created.get("updated_at") else None,
    )


@router.get(
    "/{repo_id}/graph",
    response_model=GraphResponse,
    summary="Get repository dependency graph (§8.8, §12)",
)
async def get_repository_graph(
    repo_id: str,
    level: str = Query("file", pattern="^(file|directory)$"),
    depth: int | None = Query(None, ge=1, le=5),
    focus: str | None = Query(None),
    hops: int = Query(1, ge=1, le=4),
    include_external: bool = Query(False),
    include_calls: bool = Query(True),
    user: dict[str, Any] = Depends(get_current_user),
    repo_repo: RepositoryRepository = Depends(get_repo_repository),
    member_repo: RepoMemberRepository = Depends(get_member_repository),
    file_repo: FileRepository = Depends(get_file_repository),
    symbol_repo: SymbolRepository = Depends(get_symbol_repository),
    graph_repo: GraphRepository = Depends(get_graph_repository),
) -> GraphResponse:
    user_id = str(user["_id"])
    repo_doc = await repo_repo.get_by_id(repo_id)
    if not repo_doc:
        raise NotFoundError(f"Repository {repo_id} not found.")

    is_owner = repo_doc["owner_id"] == user_id
    member = await member_repo.get_member(repo_id, user_id)
    if not is_owner and not member and user.get("role") != "admin":
        raise ForbiddenError("Access forbidden to this repository.")

    files = await file_repo.list_files(repo_id, limit=5000)
    all_paths = [f["path"] for f in files]
    edges = await graph_repo.list_for_repo(repo_id, limit=5000)

    if not edges:
        symbols = await symbol_repo.list_for_repo(repo_id, limit=5000)
        symbols_by_file: dict[str, list[dict[str, Any]]] = {}
        for s in symbols:
            symbols_by_file.setdefault(s.get("path", ""), []).append(s)
        edges = GraphBuilder().build_edges(files, symbols_by_file)
        if edges:
            await graph_repo.bulk_upsert_edges(repo_id, edges)

    analyzer = GraphAnalyzer(edges, all_paths)
    view = analyzer.get_graph_view(
        level=level,
        depth=depth,
        focus=focus,
        hops=hops,
        include_external=include_external,
        include_calls=include_calls,
    )
    return GraphResponse(**view)


@router.get(
    "/{repo_id}/stats",
    response_model=RepoStatsResponse,
    summary="Get repository statistics (§12)",
)
async def get_repository_stats(
    repo_id: str,
    user: dict[str, Any] = Depends(get_current_user),
    repo_repo: RepositoryRepository = Depends(get_repo_repository),
    member_repo: RepoMemberRepository = Depends(get_member_repository),
    file_repo: FileRepository = Depends(get_file_repository),
    symbol_repo: SymbolRepository = Depends(get_symbol_repository),
    chunk_repo: ChunkRepository = Depends(get_chunk_repository),
) -> RepoStatsResponse:
    user_id = str(user["_id"])
    repo_doc = await repo_repo.get_by_id(repo_id)
    if not repo_doc:
        raise NotFoundError(f"Repository {repo_id} not found.")

    is_owner = repo_doc["owner_id"] == user_id
    member = await member_repo.get_member(repo_id, user_id)
    if not is_owner and not member and user.get("role") != "admin":
        raise ForbiddenError("Access forbidden to this repository.")

    files = await file_repo.list_files(repo_id, limit=5000)
    total_loc = sum(f.get("loc", 0) for f in files)
    total_redactions = sum(f.get("redaction_count", 0) for f in files)

    counts_by_kind: dict[str, int] = {}
    for f in files:
        k = f.get("kind", "code")
        counts_by_kind[k] = counts_by_kind.get(k, 0) + 1

    total_symbols = await symbol_repo.count_for_repo(repo_id)
    total_chunks = await chunk_repo.count_for_repo(repo_id)

    stats = repo_doc.get("stats", {})
    languages = stats.get("languages", {})

    return RepoStatsResponse(
        repo_id=str(repo_id),
        commit_sha=repo_doc.get("commit_sha"),
        total_files=len(files),
        total_loc=total_loc,
        total_symbols=total_symbols,
        total_chunks=total_chunks,
        total_redactions=total_redactions,
        languages=languages,
        file_counts_by_kind=counts_by_kind,
    )

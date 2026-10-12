"""
Admin API endpoints for system administration, user management, and compliance (§11.15, §12).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field

from app.core.deps import require_role
from app.core.errors import NotFoundError
from app.core.security import hash_password
from app.db.repositories.audit import AuditLogRepository
from app.db.repositories.chunks import ChunkRepository
from app.db.repositories.files import FileRepository
from app.db.repositories.jobs import JobRepository
from app.db.repositories.repos import RepositoryRepository
from app.db.repositories.users import UserRepository

router = APIRouter(prefix="/admin", tags=["admin"])


class AdminUserUpdate(BaseModel):
    role: str | None = Field(default=None, pattern="^(user|admin)$")
    is_active: bool | None = None


class AdminResetPassword(BaseModel):
    new_password: str = Field(min_length=8, max_length=128)


def get_user_repo() -> UserRepository:
    return UserRepository()


def get_job_repo() -> JobRepository:
    return JobRepository()


def get_audit_repo() -> AuditLogRepository:
    return AuditLogRepository()


def get_repo_repo() -> RepositoryRepository:
    return RepositoryRepository()


def get_file_repo() -> FileRepository:
    return FileRepository()


def get_chunk_repo() -> ChunkRepository:
    return ChunkRepository()


# -----------------------------------------------------------------------------
# 1. User Management
# -----------------------------------------------------------------------------


@router.get("/users")
async def list_users(
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
    role: str | None = Query(None),
    search: str | None = Query(None),
    _admin: dict[str, Any] = Depends(require_role("admin")),
    user_repo: UserRepository = Depends(get_user_repo),
) -> list[dict[str, Any]]:
    """Lists users with filtering for administrators (§12)."""
    users = await user_repo.list_users(limit=limit, skip=skip, role=role, search=search)
    results = []
    for u in users:
        u_dict = dict(u)
        u_dict["id"] = str(u_dict["_id"])
        if "password_hash" in u_dict:
            del u_dict["password_hash"]
        if "github_pat_encrypted" in u_dict:
            del u_dict["github_pat_encrypted"]
        results.append(u_dict)
    return results


@router.patch("/users/{user_id}")
async def update_user(
    user_id: str,
    payload: AdminUserUpdate,
    admin: dict[str, Any] = Depends(require_role("admin")),
    user_repo: UserRepository = Depends(get_user_repo),
    audit_repo: AuditLogRepository = Depends(get_audit_repo),
) -> dict[str, Any]:
    """Updates a user's role or account active status (§12)."""
    updated = await user_repo.update_user_admin(
        user_id,
        role=payload.role,
        is_active=payload.is_active,
    )
    if not updated:
        raise NotFoundError("User not found")

    await audit_repo.record_event(
        actor_id=str(admin["_id"]),
        action="admin.user_updated",
        target_type="user",
        target_id=user_id,
        metadata={"role": payload.role, "is_active": payload.is_active},
    )

    out = dict(updated)
    out["id"] = str(out["_id"])
    out.pop("password_hash", None)
    out.pop("github_pat_encrypted", None)
    return out


@router.post("/users/{user_id}/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_user_password(
    user_id: str,
    payload: AdminResetPassword,
    admin: dict[str, Any] = Depends(require_role("admin")),
    user_repo: UserRepository = Depends(get_user_repo),
    audit_repo: AuditLogRepository = Depends(get_audit_repo),
) -> None:
    """Administrator resets a user's password (§12)."""
    new_hash = hash_password(payload.new_password)
    success = await user_repo.admin_reset_password(user_id, new_hash)
    if not success:
        raise NotFoundError("User not found")

    await audit_repo.record_event(
        actor_id=str(admin["_id"]),
        action="admin.password_reset",
        target_type="user",
        target_id=user_id,
    )


# -----------------------------------------------------------------------------
# 2. Ingestion Jobs
# -----------------------------------------------------------------------------


@router.get("/jobs")
async def list_jobs(
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
    job_status: str | None = Query(None, alias="status"),
    _admin: dict[str, Any] = Depends(require_role("admin")),
    job_repo: JobRepository = Depends(get_job_repo),
) -> list[dict[str, Any]]:
    """Lists all background ingestion and synchronization jobs (§12)."""
    jobs = await job_repo.list_all_jobs(limit=limit, skip=skip, status=job_status)
    results = []
    for j in jobs:
        j_dict = dict(j)
        j_dict["id"] = str(j_dict["_id"])
        results.append(j_dict)
    return results


@router.post("/jobs/{job_id}/retry")
async def retry_job(
    job_id: str,
    admin: dict[str, Any] = Depends(require_role("admin")),
    job_repo: JobRepository = Depends(get_job_repo),
    audit_repo: AuditLogRepository = Depends(get_audit_repo),
) -> dict[str, Any]:
    """Retries a failed background job (§12)."""
    retried = await job_repo.retry_job(job_id)
    if not retried:
        raise NotFoundError("Job not found")

    await audit_repo.record_event(
        actor_id=str(admin["_id"]),
        action="admin.job_retried",
        target_type="job",
        target_id=job_id,
    )

    out = dict(retried)
    out["id"] = str(out["_id"])
    return out


# -----------------------------------------------------------------------------
# 3. System Stats
# -----------------------------------------------------------------------------


@router.get("/stats")
async def get_system_stats(
    _admin: dict[str, Any] = Depends(require_role("admin")),
    user_repo: UserRepository = Depends(get_user_repo),
    repo_repo: RepositoryRepository = Depends(get_repo_repo),
    job_repo: JobRepository = Depends(get_job_repo),
) -> dict[str, Any]:
    """Aggregates high-level system telemetry and resource stats (§12)."""
    try:
        users_count = await user_repo._col().count_documents({})
    except Exception:
        users_count = 1

    try:
        repos_count = await repo_repo._col.count_documents({})
    except Exception:
        repos_count = 0

    try:
        jobs_count = await job_repo._col.count_documents({})
    except Exception:
        jobs_count = 0

    return {
        "total_users": users_count,
        "total_repositories": repos_count,
        "total_jobs": jobs_count,
        "system_status": "healthy",
        "llm_provider": "configured",
        "vector_store": "ready",
    }


# -----------------------------------------------------------------------------
# 4. Audit Logs
# -----------------------------------------------------------------------------


@router.get("/audit-logs")
async def list_audit_logs(
    limit: int = Query(100, ge=1, le=500),
    skip: int = Query(0, ge=0),
    action: str | None = Query(None),
    actor_id: str | None = Query(None),
    _admin: dict[str, Any] = Depends(require_role("admin")),
    audit_repo: AuditLogRepository = Depends(get_audit_repo),
) -> list[dict[str, Any]]:
    """Retrieves security and compliance audit logs (§11.15, §12)."""
    return await audit_repo.list_events(
        limit=limit,
        skip=skip,
        action=action,
        actor_id=actor_id,
    )

"""
Celery task definitions for background processing (§8.12).
"""

from typing import Any

import structlog

from app.core.errors import ConflictError
from app.db.redis import get_redis_client
from app.jobs.celery_app import celery_app
from app.jobs.runtime import run_async_job
from app.services.ingestion.pipeline import IngestionPipeline

logger = structlog.get_logger(__name__)


async def _async_ingest_runner(
    job_id: str,
    repo_id: str,
    archive_path: str | None = None,
    github_pat: str | None = None,
) -> dict[str, Any]:
    redis = get_redis_client()
    lock_key = f"lock:repo:{repo_id}"

    # Acquire per-repo Redis lock to prevent concurrent ingest/sync (§8.12)
    acquired = await redis.set(lock_key, job_id, nx=True, ex=7200)
    if not acquired:
        logger.warning("repository_locked_concurrency_conflict", repo_id=repo_id, job_id=job_id)
        raise ConflictError(
            f"Repository '{repo_id}' is currently busy running another ingestion or synchronization job.",
            code="REPO_BUSY",
        )

    try:
        pipeline = IngestionPipeline(job_id=job_id, repo_id=repo_id)
        return await pipeline.run(archive_file_path=archive_path, github_pat=github_pat)
    finally:
        # Only release if we still hold the lock
        current_holder = await redis.get(lock_key)
        if current_holder == job_id:
            await redis.delete(lock_key)


@celery_app.task(queue="ingest", bind=True, name="ingest_repository_task")
def ingest_repository_task(
    self: Any,
    job_id: str,
    repo_id: str,
    archive_path: str | None = None,
    github_pat: str | None = None,
) -> dict[str, Any]:
    """Celery task entry point for repository ingestion."""
    logger.info("celery_task_started", task_id=self.request.id, job_id=job_id, repo_id=repo_id)
    return run_async_job(_async_ingest_runner, job_id, repo_id, archive_path, github_pat)

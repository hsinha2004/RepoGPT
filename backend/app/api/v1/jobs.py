"""
Background jobs API endpoints and Server-Sent Events (SSE) streaming (§8.11 & §12).
"""

import asyncio
import json
from collections.abc import AsyncGenerator
from typing import Any

import structlog
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.core.deps import get_current_user
from app.core.errors import NotFoundError
from app.db.redis import get_redis_client
from app.db.repositories.jobs import JobRepository
from app.schemas.jobs import JobError, JobResponse

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/jobs", tags=["jobs"])


def get_job_repository() -> JobRepository:
    return JobRepository()


def _format_job_response(doc: dict[str, Any]) -> JobResponse:
    err = None
    if doc.get("error"):
        err = JobError(
            code=doc["error"].get("code", "ERROR"), message=doc["error"].get("message", "")
        )

    return JobResponse(
        id=str(doc["_id"]),
        type=doc["type"],
        repo_id=str(doc["repo_id"]),
        user_id=str(doc["user_id"]),
        status=doc.get("status", "queued"),
        stage=doc.get("stage", "queued"),
        progress=doc.get("progress", 0),
        message=doc.get("message", ""),
        counters=doc.get("counters", {}),
        warnings=doc.get("warnings", []),
        error=err,
        cancel_requested=doc.get("cancel_requested", False),
        created_at=doc["created_at"],
        started_at=doc.get("started_at"),
        finished_at=doc.get("finished_at"),
    )


@router.get("/{job_id}", response_model=JobResponse, summary="Get job status")
async def get_job(
    job_id: str,
    _user: dict[str, Any] = Depends(get_current_user),
    job_repo: JobRepository = Depends(get_job_repository),
) -> JobResponse:
    """Fetches current state, stage, and counters of a background job."""
    job_doc = await job_repo.get_by_id(job_id)
    if not job_doc:
        raise NotFoundError(f"Job {job_id} not found.")
    return _format_job_response(job_doc)


@router.post("/{job_id}/cancel", response_model=JobResponse, summary="Cancel job")
async def cancel_job(
    job_id: str,
    _user: dict[str, Any] = Depends(get_current_user),
    job_repo: JobRepository = Depends(get_job_repository),
) -> JobResponse:
    """Requests cooperative cancellation of a running background job."""
    job_doc = await job_repo.get_by_id(job_id)
    if not job_doc:
        raise NotFoundError(f"Job {job_id} not found.")

    await job_repo.request_cancel(job_id)
    updated = await job_repo.get_by_id(job_id)
    return _format_job_response(updated or job_doc)


@router.get("/{job_id}/events", summary="Stream job progress events via SSE")
async def stream_job_events(
    job_id: str,
    _user: dict[str, Any] = Depends(get_current_user),
    job_repo: JobRepository = Depends(get_job_repository),
) -> StreamingResponse:
    """
    Server-Sent Events endpoint streaming real-time progress events for a job.
    Subscribes to Redis pub/sub channel 'job:{job_id}' and yields formatted SSE chunks.
    """
    job_doc = await job_repo.get_by_id(job_id)
    if not job_doc:
        raise NotFoundError(f"Job {job_id} not found.")

    async def event_generator() -> AsyncGenerator[str, None]:
        redis = get_redis_client()
        pubsub = redis.pubsub()
        channel = f"job:{job_id}"
        await pubsub.subscribe(channel)

        try:
            # Yield initial snapshot immediately
            initial_data = {
                "job_id": str(job_doc["_id"]),
                "repo_id": str(job_doc["repo_id"]),
                "stage": job_doc.get("stage", "queued"),
                "progress": job_doc.get("progress", 0),
                "message": job_doc.get("message", ""),
                "counters": job_doc.get("counters", {}),
                "warnings": job_doc.get("warnings", []),
                "status": job_doc.get("status", "queued"),
            }
            yield f"event: progress\ndata: {json.dumps(initial_data)}\n\n"

            # If job has already completed, close stream immediately
            if job_doc.get("status") in ("succeeded", "failed", "cancelled"):
                return

            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and message.get("type") == "message":
                    raw_data = message.get("data")
                    if isinstance(raw_data, bytes):
                        raw_data = raw_data.decode("utf-8")
                    yield f"event: progress\ndata: {raw_data}\n\n"

                    try:
                        parsed = json.loads(raw_data)
                        if parsed.get("status") in ("succeeded", "failed", "cancelled"):
                            break
                    except Exception:
                        pass
                else:
                    # Keepalive ping
                    yield ": ping\n\n"

                # Check database status periodically as fallback
                current_job = await job_repo.get_by_id(job_id)
                if current_job and current_job.get("status") in (
                    "succeeded",
                    "failed",
                    "cancelled",
                ):
                    final_data = {
                        "job_id": job_id,
                        "repo_id": str(current_job["repo_id"]),
                        "stage": current_job.get("stage", "finished"),
                        "progress": current_job.get("progress", 100),
                        "message": current_job.get("message", ""),
                        "counters": current_job.get("counters", {}),
                        "warnings": current_job.get("warnings", []),
                        "status": current_job.get("status"),
                    }
                    yield f"event: progress\ndata: {json.dumps(final_data)}\n\n"
                    break

                await asyncio.sleep(0.5)

        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

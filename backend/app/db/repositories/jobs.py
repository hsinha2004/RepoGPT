"""
Repository MongoDB operations for jobs collection (§6.2).
"""

from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from pymongo.asynchronous.collection import AsyncCollection

from app.core.ids import to_object_id
from app.db.mongo import get_collection


class JobRepository:
    def __init__(self, collection: AsyncCollection[Any] | None = None) -> None:
        self._col_raw = collection

    @property
    def _col(self) -> AsyncCollection[Any]:
        if self._col_raw is not None:
            return self._col_raw
        return get_collection("jobs")

    async def create_job(
        self,
        job_type: str,
        repo_id: str | ObjectId,
        user_id: str,
        celery_task_id: str | None = None,
    ) -> dict[str, Any]:
        """Creates a new job in 'queued' state."""
        now = datetime.now(UTC)
        rid = str(repo_id)
        doc: dict[str, Any] = {
            "type": job_type,
            "repo_id": rid,
            "user_id": user_id,
            "status": "queued",
            "stage": "queued",
            "progress": 0,
            "message": "Job queued for processing",
            "counters": {},
            "warnings": [],
            "error": None,
            "result_ref": None,
            "celery_task_id": celery_task_id,
            "cancel_requested": False,
            "created_at": now,
            "started_at": None,
            "finished_at": None,
        }
        result = await self._col.insert_one(doc)
        doc["_id"] = result.inserted_id
        return doc

    async def get_by_id(self, job_id: str | ObjectId) -> dict[str, Any] | None:
        """Fetches job by ObjectId."""
        oid = to_object_id(job_id)
        return await self._col.find_one({"_id": oid})

    async def mark_running(
        self,
        job_id: str | ObjectId,
        celery_task_id: str | None = None,
        stage: str = "started",
    ) -> bool:
        """Transitions job to 'running' status."""
        oid = to_object_id(job_id)
        now = datetime.now(UTC)
        update_data: dict[str, Any] = {
            "status": "running",
            "stage": stage,
            "started_at": now,
            "message": f"Job processing stage: {stage}",
        }
        if celery_task_id:
            update_data["celery_task_id"] = celery_task_id

        result = await self._col.update_one({"_id": oid}, {"$set": update_data})
        return result.modified_count > 0

    async def update_progress(
        self,
        job_id: str | ObjectId,
        stage: str,
        progress: int,
        message: str = "",
        counters: dict[str, Any] | None = None,
        warnings: list[str] | None = None,
    ) -> bool:
        """Updates progress percentage, active stage, and metrics counters."""
        oid = to_object_id(job_id)
        update_data: dict[str, Any] = {
            "stage": stage,
            "progress": min(100, max(0, progress)),
            "message": message,
        }
        if counters is not None:
            update_data["counters"] = counters

        doc_update: dict[str, Any] = {"$set": update_data}
        if warnings:
            doc_update["$push"] = {"warnings": {"$each": warnings}}

        result = await self._col.update_one({"_id": oid}, doc_update)
        return result.modified_count > 0

    async def mark_succeeded(
        self,
        job_id: str | ObjectId,
        result_ref: str | None = None,
        counters: dict[str, Any] | None = None,
    ) -> bool:
        """Marks job as successfully finished with 100% progress."""
        oid = to_object_id(job_id)
        now = datetime.now(UTC)
        update_data: dict[str, Any] = {
            "status": "succeeded",
            "progress": 100,
            "message": "Completed successfully",
            "finished_at": now,
        }
        if result_ref:
            update_data["result_ref"] = result_ref
        if counters:
            update_data["counters"] = counters

        result = await self._col.update_one({"_id": oid}, {"$set": update_data})
        return result.modified_count > 0

    async def mark_failed(
        self,
        job_id: str | ObjectId,
        code: str,
        message: str,
    ) -> bool:
        """Marks job as failed with error details."""
        oid = to_object_id(job_id)
        now = datetime.now(UTC)
        result = await self._col.update_one(
            {"_id": oid},
            {
                "$set": {
                    "status": "failed",
                    "error": {"code": code, "message": message},
                    "message": f"Failed: {message}",
                    "finished_at": now,
                }
            },
        )
        return result.modified_count > 0

    async def request_cancel(self, job_id: str | ObjectId) -> bool:
        """Signals that cancellation has been requested for this job."""
        oid = to_object_id(job_id)
        result = await self._col.update_one(
            {"_id": oid},
            {"$set": {"cancel_requested": True}},
        )
        return result.modified_count > 0

    async def is_cancel_requested(self, job_id: str | ObjectId) -> bool:
        """Checks if a cancellation signal was posted for the job."""
        job = await self.get_by_id(job_id)
        return bool(job and job.get("cancel_requested", False))

    async def mark_cancelled(self, job_id: str | ObjectId) -> bool:
        """Transitions job to 'cancelled' status."""
        oid = to_object_id(job_id)
        now = datetime.now(UTC)
        result = await self._col.update_one(
            {"_id": oid},
            {
                "$set": {
                    "status": "cancelled",
                    "message": "Job cancelled by user request",
                    "finished_at": now,
                }
            },
        )
        return result.modified_count > 0

    async def list_for_repo(
        self,
        repo_id: str | ObjectId,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Lists latest jobs executed on the repository."""
        cursor = self._col.find({"repo_id": str(repo_id)}).sort("created_at", -1).limit(limit)
        return await cursor.to_list(length=limit)

    async def list_all_jobs(
        self,
        limit: int = 50,
        skip: int = 0,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        """Lists all background jobs with optional status filtering."""
        query: dict[str, Any] = {}
        if status:
            query["status"] = status
        cursor = self._col.find(query).sort("created_at", -1).skip(skip).limit(limit)
        return await cursor.to_list(length=limit)

    async def retry_job(self, job_id: str | ObjectId) -> dict[str, Any] | None:
        """Resets a failed job to 'queued' state for worker pick up."""
        oid = to_object_id(job_id)
        now = datetime.now(UTC)
        res = await self._col.find_one_and_update(
            {"_id": oid},
            {
                "$set": {
                    "status": "queued",
                    "stage": "queued",
                    "progress": 0,
                    "message": "Job re-queued by administrator",
                    "error": None,
                    "cancel_requested": False,
                    "started_at": None,
                    "finished_at": None,
                    "updated_at": now,
                }
            },
            return_document=True,
        )
        return res

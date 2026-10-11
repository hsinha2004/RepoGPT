"""
Repository MongoDB operations for repositories collection (§6.2).
"""

from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from pymongo.asynchronous.collection import AsyncCollection

from app.core.ids import to_object_id
from app.db.mongo import get_collection


class RepositoryRepository:
    def __init__(self, collection: AsyncCollection | None = None) -> None:
        self._col = collection if collection is not None else get_collection("repositories")

    async def create_repository(
        self,
        owner_id: str,
        source: dict[str, Any],
        display_name: str,
        description: str = "",
        embedding_config: dict[str, Any] | None = None,
        settings: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Creates a new repository record with status 'queued'."""
        now = datetime.now(UTC)
        doc: dict[str, Any] = {
            "owner_id": owner_id,
            "source": source,
            "display_name": display_name,
            "description": description,
            "commit_sha": None,
            "status": "queued",
            "status_message": "Repository queued for ingestion",
            "stats": {
                "files_total": 0,
                "files_indexed": 0,
                "files_skipped": 0,
                "loc": 0,
                "symbols": 0,
                "chunks": 0,
                "languages": {},
                "redactions": 0,
            },
            "embedding": embedding_config
            or {
                "provider": "fastembed",
                "model": "BAAI/bge-small-en-v1.5",
                "dim": 384,
            },
            "settings": settings
            or {
                "auto_review": False,
                "extra_ignore_patterns": [],
            },
            "last_indexed_at": None,
            "created_at": now,
            "updated_at": now,
        }

        result = await self._col.insert_one(doc)
        doc["_id"] = result.inserted_id
        return doc

    async def get_by_id(self, repo_id: str | ObjectId) -> dict[str, Any] | None:
        """Fetch repository by its string ID or ObjectId."""
        oid = to_object_id(repo_id)
        return await self._col.find_one({"_id": oid})

    async def list_for_user(
        self,
        user_id: str,
        accessible_repo_ids: list[str] | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[dict[str, Any]], int]:
        """
        List repositories owned by user or shared with user.
        Returns (list_of_repos, total_count).
        """
        filter_query: dict[str, Any] = {"owner_id": user_id}
        if accessible_repo_ids:
            all_ids = [to_object_id(rid) for rid in accessible_repo_ids]
            filter_query = {
                "$or": [
                    {"owner_id": user_id},
                    {"_id": {"$in": all_ids}},
                ]
            }

        total = await self._col.count_documents(filter_query)
        cursor = self._col.find(filter_query).sort("created_at", -1).skip(skip).limit(limit)
        repos = await cursor.to_list(length=limit)
        return repos, total

    async def update_status(
        self,
        repo_id: str | ObjectId,
        status: str,
        status_message: str | None = None,
        commit_sha: str | None = None,
        indexed_model: str | None = None,
    ) -> bool:
        """Update repository ingestion status, commit_sha, and indexed_model."""
        oid = to_object_id(repo_id)
        update_data: dict[str, Any] = {
            "status": status,
            "updated_at": datetime.now(UTC),
        }
        if status_message is not None:
            update_data["status_message"] = status_message
        if commit_sha is not None:
            update_data["commit_sha"] = commit_sha
        if indexed_model is not None:
            update_data["indexed_model"] = indexed_model
        if status == "ready":
            update_data["last_indexed_at"] = datetime.now(UTC)

        result = await self._col.update_one({"_id": oid}, {"$set": update_data})
        return result.modified_count > 0

    async def update_stats(self, repo_id: str | ObjectId, stats: dict[str, Any]) -> bool:
        """Update repository file and chunk statistics."""
        oid = to_object_id(repo_id)
        result = await self._col.update_one(
            {"_id": oid},
            {"$set": {"stats": stats, "updated_at": datetime.now(UTC)}},
        )
        return result.modified_count > 0

    async def update_settings(self, repo_id: str | ObjectId, settings: dict[str, Any]) -> bool:
        """Update repository settings (e.g., extra_ignore_patterns, auto_review)."""
        oid = to_object_id(repo_id)
        result = await self._col.update_one(
            {"_id": oid},
            {"$set": {"settings": settings, "updated_at": datetime.now(UTC)}},
        )
        return result.modified_count > 0

    async def delete_repository(self, repo_id: str | ObjectId) -> bool:
        """Permanently delete repository record."""
        oid = to_object_id(repo_id)
        result = await self._col.delete_one({"_id": oid})
        return result.deleted_count > 0

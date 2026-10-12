from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from pymongo.asynchronous.collection import AsyncCollection

from app.db.mongo import get_collection


class OverviewRepository:
    """Repository for persisting and retrieving repository onboarding overviews (§8.9)."""

    def __init__(self, collection: AsyncCollection | None = None) -> None:
        if collection is not None:
            self._col: AsyncCollection | None = collection
        else:
            try:
                self._col = get_collection("repo_overviews")
            except Exception:
                self._col = None

    async def get_by_repo(self, repo_id: str | ObjectId) -> dict[str, Any] | None:
        """Retrieves the latest generated overview for a repository."""
        if self._col is None:
            return None
        return await self._col.find_one({"repo_id": str(repo_id)})

    async def upsert(
        self,
        repo_id: str | ObjectId,
        commit_sha: str,
        overview_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Upserts an overview document for a repository commit."""
        now = datetime.now(UTC)
        rid = str(repo_id)
        doc: dict[str, Any] = {
            "repo_id": rid,
            "commit_sha": commit_sha,
            "markdown": overview_data.get("markdown", ""),
            "suggested_questions": overview_data.get("suggested_questions", []),
            "sources": overview_data.get("sources", []),
            "tech_stack": overview_data.get("tech_stack", []),
            "entry_points": overview_data.get("entry_points", []),
            "reading_order": overview_data.get("reading_order", []),
            "updated_at": now,
        }

        if self._col is None:
            return doc

        res = await self._col.find_one_and_update(
            {"repo_id": rid},
            {
                "$set": doc,
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
            return_document=True,
        )
        return res or doc

    async def delete_by_repo(self, repo_id: str | ObjectId) -> int:
        """Deletes overviews associated with a repository."""
        if self._col is None:
            return 0
        res = await self._col.delete_many({"repo_id": str(repo_id)})
        return res.deleted_count

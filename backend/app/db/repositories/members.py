"""
Repository MongoDB operations for repo_members collection (§6.2).
"""

from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from pymongo.asynchronous.collection import AsyncCollection

from app.db.mongo import get_collection


class RepoMemberRepository:
    def __init__(self, collection: AsyncCollection | None = None) -> None:
        self._col = collection if collection is not None else get_collection("repo_members")

    async def add_member(
        self,
        repo_id: str | ObjectId,
        user_id: str,
        role: str,
        added_by: str,
    ) -> dict[str, Any]:
        """Adds a user as a member of a repository with a role ('viewer' | 'editor' | 'owner')."""
        now = datetime.now(UTC)
        rid = str(repo_id)
        doc: dict[str, Any] = {
            "repo_id": rid,
            "user_id": user_id,
            "role": role,
            "added_by": added_by,
            "created_at": now,
        }
        await self._col.update_one(
            {"repo_id": rid, "user_id": user_id},
            {"$set": doc},
            upsert=True,
        )
        return doc

    async def get_member(self, repo_id: str | ObjectId, user_id: str) -> dict[str, Any] | None:
        """Finds membership record for a given user and repo."""
        return await self._col.find_one({"repo_id": str(repo_id), "user_id": user_id})

    async def list_members(self, repo_id: str | ObjectId) -> list[dict[str, Any]]:
        """Lists all members belonging to a repository."""
        cursor = self._col.find({"repo_id": str(repo_id)}).sort("created_at", 1)
        return await cursor.to_list(length=100)

    async def update_role(self, repo_id: str | ObjectId, user_id: str, role: str) -> bool:
        """Updates a member's role."""
        result = await self._col.update_one(
            {"repo_id": str(repo_id), "user_id": user_id},
            {"$set": {"role": role, "updated_at": datetime.now(UTC)}},
        )
        return result.modified_count > 0

    async def remove_member(self, repo_id: str | ObjectId, user_id: str) -> bool:
        """Removes a user's membership from a repository."""
        result = await self._col.delete_one({"repo_id": str(repo_id), "user_id": user_id})
        return result.deleted_count > 0

    async def get_user_repo_ids(self, user_id: str) -> list[str]:
        """Returns all repository IDs where the user is an explicit member."""
        cursor = self._col.find({"user_id": user_id}, {"repo_id": 1})
        docs = await cursor.to_list(length=500)
        return [d["repo_id"] for d in docs if "repo_id" in d]

    async def delete_all_for_repo(self, repo_id: str | ObjectId) -> int:
        """Deletes all member records for a repository upon repo deletion."""
        result = await self._col.delete_many({"repo_id": str(repo_id)})
        return result.deleted_count

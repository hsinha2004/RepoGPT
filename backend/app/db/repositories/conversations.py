from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from bson import ObjectId

from app.db.mongo import get_collection


class ConversationRepository:
    """MongoDB repository for the conversations collection (§6.2, §9.9)."""

    def __init__(self, collection: Any | None = None) -> None:
        self._col = collection if collection is not None else get_collection("conversations")

    async def create(self, repo_id: str, user_id: str, title: str) -> dict[str, Any]:
        now = datetime.now(UTC)
        doc = {
            "repo_id": repo_id,
            "user_id": user_id,
            "title": title,
            "message_count": 0,
            "created_at": now,
            "updated_at": now,
        }
        res = await self._col.insert_one(doc)
        doc["_id"] = res.inserted_id
        return doc

    async def get_by_id(self, conversation_id: str) -> dict[str, Any] | None:
        try:
            return await self._col.find_one({"_id": ObjectId(conversation_id)})
        except Exception:
            return await self._col.find_one({"_id": conversation_id})

    async def list_by_repo_user(
        self,
        repo_id: str,
        user_id: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        cursor = (
            self._col.find({"repo_id": repo_id, "user_id": user_id})
            .sort("updated_at", -1)
            .limit(limit)
        )
        return await cursor.to_list(length=limit)

    async def update_title(self, conversation_id: str, title: str) -> bool:
        now = datetime.now(UTC)
        q: dict[str, Any]
        try:
            q = {"_id": ObjectId(conversation_id)}
        except Exception:
            q = {"_id": conversation_id}

        res = await self._col.update_one(q, {"$set": {"title": title, "updated_at": now}})
        return res.modified_count > 0

    async def increment_message_count(self, conversation_id: str, delta: int = 1) -> None:
        now = datetime.now(UTC)
        q: dict[str, Any]
        try:
            q = {"_id": ObjectId(conversation_id)}
        except Exception:
            q = {"_id": conversation_id}

        await self._col.update_one(
            q, {"$inc": {"message_count": delta}, "$set": {"updated_at": now}}
        )

    async def delete(self, conversation_id: str) -> bool:
        q: dict[str, Any]
        try:
            q = {"_id": ObjectId(conversation_id)}
        except Exception:
            q = {"_id": conversation_id}

        res = await self._col.delete_one(q)
        return res.deleted_count > 0

    async def delete_by_repo(self, repo_id: str) -> int:
        res = await self._col.delete_many({"repo_id": repo_id})
        return res.deleted_count

    async def delete_by_user(self, user_id: str) -> int:
        res = await self._col.delete_many({"user_id": user_id})
        return res.deleted_count

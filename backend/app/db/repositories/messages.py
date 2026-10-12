from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from bson import ObjectId

from app.db.mongo import get_collection


class MessageRepository:
    """MongoDB repository for the messages collection (§6.2, §9.9)."""

    def __init__(self, collection: Any | None = None) -> None:
        self._col_raw = collection

    @property
    def _col(self) -> Any:
        if self._col_raw is not None:
            return self._col_raw
        return get_collection("messages")

    async def create(
        self,
        conversation_id: str,
        user_id: str,
        role: str,
        content: str,
        status: str = "complete",
        route: dict[str, Any] | None = None,
        sources: list[dict[str, Any]] | None = None,
        citations: list[dict[str, Any]] | None = None,
        confidence: dict[str, Any] | None = None,
        usage: dict[str, Any] | None = None,
        latency_ms: dict[str, float] | None = None,
        trace: dict[str, Any] | None = None,
        cached: bool = False,
    ) -> dict[str, Any]:
        now = datetime.now(UTC)
        doc: dict[str, Any] = {
            "conversation_id": conversation_id,
            "user_id": user_id,
            "role": role,
            "content": content,
            "status": status,
            "route": route,
            "sources": sources or [],
            "citations": citations or [],
            "confidence": confidence,
            "usage": usage,
            "latency_ms": latency_ms or {},
            "trace": trace or {},
            "cached": cached,
            "feedback": None,
            "created_at": now,
        }
        res = await self._col.insert_one(doc)
        doc["_id"] = res.inserted_id
        return doc

    async def get_by_id(self, message_id: str) -> dict[str, Any] | None:
        try:
            return await self._col.find_one({"_id": ObjectId(message_id)})
        except Exception:
            return await self._col.find_one({"_id": message_id})

    async def list_by_conversation(
        self,
        conversation_id: str,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        cursor = (
            self._col.find({"conversation_id": conversation_id}).sort("created_at", 1).limit(limit)
        )
        return await cursor.to_list(length=limit)

    async def update_feedback(
        self,
        message_id: str,
        rating: str,
        comment: str | None = None,
    ) -> bool:
        now = datetime.now(UTC)
        feedback_doc = {
            "rating": rating,
            "comment": comment,
            "at": now,
        }
        q: dict[str, Any]
        try:
            q = {"_id": ObjectId(message_id)}
        except Exception:
            q = {"_id": message_id}

        res = await self._col.update_one(q, {"$set": {"feedback": feedback_doc}})
        return res.modified_count > 0

    async def update_status(
        self,
        message_id: str,
        status: str,
        content: str | None = None,
    ) -> bool:
        q: dict[str, Any]
        try:
            q = {"_id": ObjectId(message_id)}
        except Exception:
            q = {"_id": message_id}

        upd: dict[str, Any] = {"status": status}
        if content is not None:
            upd["content"] = content

        res = await self._col.update_one(q, {"$set": upd})
        return res.modified_count > 0

    async def delete_by_conversation(self, conversation_id: str) -> int:
        res = await self._col.delete_many({"conversation_id": conversation_id})
        return res.deleted_count

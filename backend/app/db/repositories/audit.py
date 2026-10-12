"""
Audit log database repository for compliance and security activity tracking.
"""

from datetime import UTC, datetime
from typing import Any

from app.db.mongo import get_collection

_IN_MEMORY_AUDIT_LOGS: list[dict[str, Any]] = []


class AuditLogRepository:
    def __init__(self) -> None:
        self.collection_name = "audit_logs"

    def _col(self) -> Any:
        try:
            return get_collection(self.collection_name)
        except Exception:
            return None

    async def record_event(
        self,
        actor_id: str,
        action: str,
        target_type: str,
        target_id: str,
        ip: str = "",
        user_agent: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        now = datetime.now(UTC)
        doc: dict[str, Any] = {
            "actor_id": actor_id,
            "action": action,
            "target_type": target_type,
            "target_id": target_id,
            "ip": ip,
            "user_agent": user_agent,
            "metadata": metadata or {},
            "created_at": now.isoformat(),
        }
        col = self._col()
        if col is not None:
            res = await col.insert_one(doc)
            doc["_id"] = str(res.inserted_id)
        else:
            import uuid

            doc["_id"] = str(uuid.uuid4())
            _IN_MEMORY_AUDIT_LOGS.insert(0, doc)
        return doc

    async def list_events(
        self,
        limit: int = 100,
        skip: int = 0,
        action: str | None = None,
        actor_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Lists audit events ordered by newest first."""
        col = self._col()
        if col is not None:
            query: dict[str, Any] = {}
            if action:
                query["action"] = action
            if actor_id:
                query["actor_id"] = actor_id
            cursor = col.find(query).sort("created_at", -1).skip(skip).limit(limit)
            docs = await cursor.to_list(length=limit)
            for d in docs:
                d["_id"] = str(d["_id"])
                if isinstance(d.get("created_at"), datetime):
                    d["created_at"] = d["created_at"].isoformat()
            return docs

        filtered = [
            e
            for e in _IN_MEMORY_AUDIT_LOGS
            if (not action or e.get("action") == action)
            and (not actor_id or e.get("actor_id") == actor_id)
        ]
        return filtered[skip : skip + limit]

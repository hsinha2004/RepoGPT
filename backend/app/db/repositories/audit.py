"""
Audit log database repository for compliance and security activity tracking.
"""

from datetime import UTC, datetime
from typing import Any

from app.db.mongo import get_collection


class AuditLogRepository:
    def __init__(self) -> None:
        self.collection_name = "audit_logs"

    def _col(self) -> Any:
        return get_collection(self.collection_name)

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
            "created_at": now,
        }
        res = await self._col().insert_one(doc)
        doc["_id"] = res.inserted_id
        return doc

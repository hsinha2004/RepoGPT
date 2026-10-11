"""
Session database repository for refresh tokens and rotation family tracking.
"""

from datetime import UTC, datetime
from typing import Any

from app.db.mongo import get_collection


class SessionRepository:
    def __init__(self) -> None:
        self.collection_name = "sessions"

    def _col(self) -> Any:
        return get_collection(self.collection_name)

    async def create_session(
        self,
        user_id: str,
        family_id: str,
        token_hash: str,
        expires_at: datetime,
        user_agent: str = "",
        ip: str = "",
    ) -> dict[str, Any]:
        now = datetime.now(UTC)
        doc: dict[str, Any] = {
            "user_id": user_id,
            "family_id": family_id,
            "token_hash": token_hash,
            "expires_at": expires_at,
            "revoked_at": None,
            "replaced_by": None,
            "user_agent": user_agent,
            "ip": ip,
            "created_at": now,
        }
        res = await self._col().insert_one(doc)
        doc["_id"] = res.inserted_id
        return doc

    async def get_by_token_hash(self, token_hash: str) -> dict[str, Any] | None:
        return await self._col().find_one({"token_hash": token_hash})

    async def rotate_session(
        self,
        old_token_hash: str,
        new_token_hash: str,
        user_id: str,
        family_id: str,
        new_expires_at: datetime,
        user_agent: str = "",
        ip: str = "",
    ) -> dict[str, Any]:
        """
        Mark old token as replaced and create new active token in the same family.
        """
        now = datetime.now(UTC)
        # Mark old token replaced
        await self._col().update_one(
            {"token_hash": old_token_hash},
            {"$set": {"replaced_by": new_token_hash, "revoked_at": now}},
        )

        # Create new session doc
        return await self.create_session(
            user_id=user_id,
            family_id=family_id,
            token_hash=new_token_hash,
            expires_at=new_expires_at,
            user_agent=user_agent,
            ip=ip,
        )

    async def revoke_family(self, family_id: str) -> int:
        """
        Theft detection: when reuse of an already-rotated token is detected,
        revoke all sessions in the entire family.
        """
        now = datetime.now(UTC)
        res = await self._col().update_many(
            {"family_id": family_id, "revoked_at": None},
            {"$set": {"revoked_at": now}},
        )
        return int(res.modified_count)

    async def revoke_token(self, token_hash: str) -> bool:
        now = datetime.now(UTC)
        res = await self._col().update_one(
            {"token_hash": token_hash, "revoked_at": None},
            {"$set": {"revoked_at": now}},
        )
        return res.modified_count > 0

    async def revoke_all_for_user(self, user_id: str) -> int:
        now = datetime.now(UTC)
        res = await self._col().update_many(
            {"user_id": user_id, "revoked_at": None},
            {"$set": {"revoked_at": now}},
        )
        return int(res.modified_count)

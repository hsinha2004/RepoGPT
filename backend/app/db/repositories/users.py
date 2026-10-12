"""
User database repository for MongoDB users collection.
"""

from datetime import UTC, datetime
from typing import Any

from bson import ObjectId

from app.db.mongo import get_collection


class UserRepository:
    def __init__(self) -> None:
        self.collection_name = "users"

    def _col(self) -> Any:
        return get_collection(self.collection_name)

    async def get_by_id(self, user_id: str) -> dict[str, Any] | None:
        try:
            return await self._col().find_one({"_id": ObjectId(user_id)})
        except Exception:
            return await self._col().find_one({"_id": user_id})

    async def get_by_email(self, email: str) -> dict[str, Any] | None:
        return await self._col().find_one({"email": email.lower().strip()})

    async def get_by_github_id(self, github_id: int) -> dict[str, Any] | None:
        return await self._col().find_one({"github.id": github_id})

    async def create_user(
        self,
        email: str,
        name: str,
        password_hash: str | None,
        role: str = "user",
        github: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        now = datetime.now(UTC)
        doc: dict[str, Any] = {
            "email": email.lower().strip(),
            "name": name.strip(),
            "password_hash": password_hash,
            "role": role,
            "is_active": True,
            "github": github,
            "github_pat_encrypted": None,
            "github_pat_last4": None,
            "quotas": {
                "questions_per_day": 200,
                "ingestions_per_day": 10,
                "reviews_per_day": 20,
                "tokens_per_day": 1000000,
            },
            "failed_login_count": 0,
            "locked_until": None,
            "must_change_password": False,
            "last_login_at": None,
            "created_at": now,
            "updated_at": now,
        }
        res = await self._col().insert_one(doc)
        doc["_id"] = res.inserted_id
        return doc

    async def update_profile(self, user_id: str, name: str) -> bool:
        res = await self._col().update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"name": name, "updated_at": datetime.now(UTC)}},
        )
        return res.modified_count > 0

    async def update_password(self, user_id: str, password_hash: str) -> bool:
        res = await self._col().update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "password_hash": password_hash,
                    "must_change_password": False,
                    "failed_login_count": 0,
                    "locked_until": None,
                    "updated_at": datetime.now(UTC),
                }
            },
        )
        return res.modified_count > 0

    async def record_login_success(self, user_id: str) -> None:
        await self._col().update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "failed_login_count": 0,
                    "locked_until": None,
                    "last_login_at": datetime.now(UTC),
                    "updated_at": datetime.now(UTC),
                }
            },
        )

    async def record_login_failure(self, user_id: str, lock_minutes: int = 15) -> tuple[int, bool]:
        """Increment failure count, lock if reaches 10. Returns (count, is_locked)."""
        user = await self.get_by_id(user_id)
        if not user:
            return 0, False

        count = user.get("failed_login_count", 0) + 1
        now = datetime.now(UTC)
        locked_until = None
        is_locked = False

        if count >= 10:
            from datetime import timedelta

            locked_until = now + timedelta(minutes=lock_minutes)
            is_locked = True

        await self._col().update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "failed_login_count": count,
                    "locked_until": locked_until,
                    "updated_at": now,
                }
            },
        )
        return count, is_locked

    async def set_github_pat(self, user_id: str, encrypted_pat: str, last4: str) -> bool:
        res = await self._col().update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "github_pat_encrypted": encrypted_pat,
                    "github_pat_last4": last4,
                    "updated_at": datetime.now(UTC),
                }
            },
        )
        return res.modified_count > 0

    async def remove_github_pat(self, user_id: str) -> bool:
        res = await self._col().update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "github_pat_encrypted": None,
                    "github_pat_last4": None,
                    "updated_at": datetime.now(UTC),
                }
            },
        )
        return res.modified_count > 0

    async def delete_user(self, user_id: str) -> bool:
        res = await self._col().delete_one({"_id": ObjectId(user_id)})
        return res.deleted_count > 0

    async def list_users(
        self,
        limit: int = 50,
        skip: int = 0,
        role: str | None = None,
        search: str | None = None,
    ) -> list[dict[str, Any]]:
        """Lists users with optional role and search filtering."""
        query: dict[str, Any] = {}
        if role:
            query["role"] = role
        if search:
            import re

            regex = re.compile(re.escape(search), re.IGNORECASE)
            query["$or"] = [{"email": regex}, {"name": regex}]
        cursor = self._col().find(query).sort("created_at", -1).skip(skip).limit(limit)
        return await cursor.to_list(length=limit)

    async def update_user_admin(
        self,
        user_id: str,
        role: str | None = None,
        is_active: bool | None = None,
    ) -> dict[str, Any] | None:
        """Admin update of user role or active status."""
        updates: dict[str, Any] = {"updated_at": datetime.now(UTC)}
        if role is not None:
            updates["role"] = role
        if is_active is not None:
            updates["is_active"] = is_active
        res = await self._col().find_one_and_update(
            {"_id": ObjectId(user_id)},
            {"$set": updates},
            return_document=True,
        )
        return res

    async def admin_reset_password(self, user_id: str, new_password_hash: str) -> bool:
        """Admin resets a user's password."""
        res = await self._col().update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "password_hash": new_password_hash,
                    "failed_login_count": 0,
                    "locked_until": None,
                    "must_change_password": True,
                    "updated_at": datetime.now(UTC),
                }
            },
        )
        return res.modified_count > 0

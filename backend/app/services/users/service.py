"""
User account management service (profile, password, PAT, deletion, quotas).
"""

from typing import Any

import httpx

from app.core.config import get_settings
from app.core.errors import UnauthorizedError, UpstreamError, ValidationFailedError
from app.core.security import (
    encrypt_secret,
    hash_password,
    validate_password_strength,
    verify_password,
)
from app.db.repositories.audit import AuditLogRepository
from app.db.repositories.sessions import SessionRepository
from app.db.repositories.users import UserRepository


class UserService:
    def __init__(
        self,
        user_repo: UserRepository | None = None,
        session_repo: SessionRepository | None = None,
        audit_repo: AuditLogRepository | None = None,
    ) -> None:
        self.user_repo = user_repo or UserRepository()
        self.session_repo = session_repo or SessionRepository()
        self.audit_repo = audit_repo or AuditLogRepository()

    async def update_profile(self, user_id: str, name: str) -> dict[str, Any]:
        await self.user_repo.update_profile(user_id, name)
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise UnauthorizedError("User not found")
        return user

    async def change_password(self, user_id: str, current_password: str, new_password: str) -> None:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise UnauthorizedError("User not found")

        pw_hash = user.get("password_hash")
        if not pw_hash:
            raise ValidationFailedError("Account does not have a local password configured")

        is_valid, _ = verify_password(current_password, pw_hash)
        if not is_valid:
            raise UnauthorizedError("Current password does not match")

        validate_password_strength(new_password, user["email"])
        new_hash = hash_password(new_password)
        await self.user_repo.update_password(user_id, new_hash)
        await self.audit_repo.record_event(
            actor_id=user_id,
            action="user.password_changed",
            target_type="user",
            target_id=user_id,
        )

    async def set_github_pat(self, user_id: str, pat: str) -> dict[str, Any]:
        last4 = pat[-4:] if len(pat) >= 4 else pat
        encrypted = encrypt_secret(pat)
        await self.user_repo.set_github_pat(user_id, encrypted, last4)
        await self.audit_repo.record_event(
            actor_id=user_id,
            action="user.github_pat_set",
            target_type="user",
            target_id=user_id,
            metadata={"last4": last4},
        )
        return {"has_pat": True, "last4": last4}

    async def remove_github_pat(self, user_id: str) -> dict[str, Any]:
        await self.user_repo.remove_github_pat(user_id)
        await self.audit_repo.record_event(
            actor_id=user_id,
            action="user.github_pat_removed",
            target_type="user",
            target_id=user_id,
        )
        return {"has_pat": False, "last4": None}

    async def test_github_pat(self, pat: str) -> dict[str, Any]:
        settings = get_settings()
        headers = {
            "Authorization": f"token {pat}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "RepoGPT",
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(f"{settings.GITHUB_API_URL}/user", headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    return {
                        "valid": True,
                        "login": data.get("login"),
                        "rate_limit_remaining": res.headers.get("x-ratelimit-remaining"),
                    }
                elif res.status_code == 401:
                    return {"valid": False, "message": "Invalid credentials or token expired"}
                else:
                    return {"valid": False, "message": f"GitHub returned status {res.status_code}"}
        except Exception as e:
            raise UpstreamError(f"Failed to communicate with GitHub API: {str(e)}") from e

    async def delete_account(self, user_id: str) -> None:
        """
        Delete user account and all owned assets (§7.4).
        """
        await self.session_repo.revoke_all_for_user(user_id)
        await self.user_repo.delete_user(user_id)
        await self.audit_repo.record_event(
            actor_id=user_id,
            action="user.account_deleted",
            target_type="user",
            target_id=user_id,
        )


def get_user_service() -> UserService:
    return UserService()

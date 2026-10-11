"""
Authentication service implementing Argon2id, JWT, refresh rotation, reuse detection, and CSRF.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from app.core.config import get_settings
from app.core.errors import (
    ConflictError,
    ForbiddenError,
    UnauthorizedError,
)
from app.core.security import (
    constant_time_compare,
    create_access_token,
    generate_opaque_token,
    hash_password,
    hash_token,
    validate_password_strength,
    verify_password,
)
from app.db.repositories.audit import AuditLogRepository
from app.db.repositories.sessions import SessionRepository
from app.db.repositories.users import UserRepository


class AuthService:
    def __init__(
        self,
        user_repo: UserRepository | None = None,
        session_repo: SessionRepository | None = None,
        audit_repo: AuditLogRepository | None = None,
    ) -> None:
        self.user_repo = user_repo or UserRepository()
        self.session_repo = session_repo or SessionRepository()
        self.audit_repo = audit_repo or AuditLogRepository()

    async def register(
        self,
        email: str,
        name: str,
        password: str,
        ip: str = "",
        user_agent: str = "",
    ) -> tuple[str, str, str, dict[str, Any]]:
        """
        Register a new account.
        Returns: (access_token, refresh_token, csrf_token, user_doc)
        """
        settings = get_settings()
        if not settings.ALLOW_REGISTRATION:
            raise ForbiddenError("User registration is currently disabled")

        validate_password_strength(password, email)

        existing = await self.user_repo.get_by_email(email)
        if existing:
            raise ConflictError("An account with this email address already exists")

        pw_hash = hash_password(password)
        user = await self.user_repo.create_user(email=email, name=name, password_hash=pw_hash)
        user_id = str(user["_id"])

        # Audit log
        await self.audit_repo.record_event(
            actor_id=user_id,
            action="auth.register",
            target_type="user",
            target_id=user_id,
            ip=ip,
            user_agent=user_agent,
        )

        # Issue tokens
        access_token, refresh_token, csrf_token = await self._issue_session(
            user_id, user.get("role", "user"), ip, user_agent
        )
        return access_token, refresh_token, csrf_token, user

    async def login(
        self,
        email: str,
        password: str,
        ip: str = "",
        user_agent: str = "",
    ) -> tuple[str, str, str, dict[str, Any]]:
        """
        Email/password login with lockout and constant-time security checks.
        Returns: (access_token, refresh_token, csrf_token, user_doc)
        """
        user = await self.user_repo.get_by_email(email)
        generic_error = "Invalid email or password"

        if not user:
            raise UnauthorizedError(generic_error)

        user_id = str(user["_id"])
        now = datetime.now(UTC)

        # Check account lockout (§7.4)
        locked_until = user.get("locked_until")
        if locked_until and locked_until > now:
            minutes_left = max(1, int((locked_until - now).total_seconds() / 60))
            raise UnauthorizedError(
                f"Account is temporarily locked. Try again in {minutes_left} minutes."
            )

        pw_hash = user.get("password_hash")
        if not pw_hash:
            raise UnauthorizedError(generic_error)

        is_valid, needs_rehash = verify_password(password, pw_hash)
        if not is_valid:
            _, is_locked = await self.user_repo.record_login_failure(user_id)
            await self.audit_repo.record_event(
                actor_id=user_id,
                action="auth.login_failure",
                target_type="user",
                target_id=user_id,
                ip=ip,
                user_agent=user_agent,
                metadata={"is_locked": is_locked},
            )
            if is_locked:
                raise UnauthorizedError("Too many failed attempts. Account locked for 15 minutes.")
            raise UnauthorizedError(generic_error)

        if not user.get("is_active", True):
            raise UnauthorizedError("User account is inactive or disabled")

        # Rehash if parameters changed
        if needs_rehash:
            new_hash = hash_password(password)
            await self.user_repo.update_password(user_id, new_hash)

        await self.user_repo.record_login_success(user_id)

        await self.audit_repo.record_event(
            actor_id=user_id,
            action="auth.login_success",
            target_type="user",
            target_id=user_id,
            ip=ip,
            user_agent=user_agent,
        )

        access_token, refresh_token, csrf_token = await self._issue_session(
            user_id, user.get("role", "user"), ip, user_agent
        )
        return access_token, refresh_token, csrf_token, user

    async def refresh(
        self,
        raw_refresh_token: str,
        csrf_header: str,
        csrf_cookie: str,
        ip: str = "",
        user_agent: str = "",
    ) -> tuple[str, str, str, dict[str, Any]]:
        """
        Rotate refresh token with reuse detection (theft protection) and CSRF verification.
        """
        # CSRF double-submit check
        if (
            not csrf_header
            or not csrf_cookie
            or not constant_time_compare(csrf_header, csrf_cookie)
        ):
            raise UnauthorizedError("Invalid or missing CSRF token")

        token_h = hash_token(raw_refresh_token)
        session = await self.session_repo.get_by_token_hash(token_h)

        if not session:
            raise UnauthorizedError("Invalid session")

        family_id = session.get("family_id", "")
        user_id = session.get("user_id", "")

        # Theft detection: Token reuse! (§7.4)
        if session.get("replaced_by") is not None or session.get("revoked_at") is not None:
            # Revoke entire family!
            revoked_count = await self.session_repo.revoke_family(family_id)
            await self.audit_repo.record_event(
                actor_id=user_id,
                action="auth.refresh_token_reuse_detected",
                target_type="session_family",
                target_id=family_id,
                ip=ip,
                user_agent=user_agent,
                metadata={"revoked_sessions": revoked_count},
            )
            raise UnauthorizedError("Session compromised. All sessions revoked.")

        now = datetime.now(UTC)
        if session.get("expires_at") and session["expires_at"] < now:
            raise UnauthorizedError("Session has expired")

        user = await self.user_repo.get_by_id(user_id)
        if not user or not user.get("is_active", True):
            raise UnauthorizedError("User is no longer active")

        # Rotate tokens
        settings = get_settings()
        new_refresh_token = generate_opaque_token(32)
        new_token_hash = hash_token(new_refresh_token)
        new_csrf_token = generate_opaque_token(24)
        new_expires_at = now + timedelta(days=settings.REFRESH_TTL_DAYS)

        await self.session_repo.rotate_session(
            old_token_hash=token_h,
            new_token_hash=new_token_hash,
            user_id=user_id,
            family_id=family_id,
            new_expires_at=new_expires_at,
            user_agent=user_agent,
            ip=ip,
        )

        access_token = create_access_token(user_id, user.get("role", "user"))
        return access_token, new_refresh_token, new_csrf_token, user

    async def logout(self, raw_refresh_token: str, user_id: str) -> None:
        token_h = hash_token(raw_refresh_token)
        await self.session_repo.revoke_token(token_h)
        await self.audit_repo.record_event(
            actor_id=user_id,
            action="auth.logout",
            target_type="session",
            target_id=token_h[:12],
        )

    async def logout_all(self, user_id: str) -> None:
        count = await self.session_repo.revoke_all_for_user(user_id)
        await self.audit_repo.record_event(
            actor_id=user_id,
            action="auth.logout_all",
            target_type="user",
            target_id=user_id,
            metadata={"revoked_count": count},
        )

    async def _issue_session(
        self,
        user_id: str,
        role: str,
        ip: str,
        user_agent: str,
    ) -> tuple[str, str, str]:
        settings = get_settings()
        now = datetime.now(UTC)
        family_id = generate_opaque_token(16)
        refresh_token = generate_opaque_token(32)
        csrf_token = generate_opaque_token(24)
        token_h = hash_token(refresh_token)
        expires_at = now + timedelta(days=settings.REFRESH_TTL_DAYS)

        await self.session_repo.create_session(
            user_id=user_id,
            family_id=family_id,
            token_hash=token_h,
            expires_at=expires_at,
            user_agent=user_agent,
            ip=ip,
        )

        access_token = create_access_token(user_id, role)
        return access_token, refresh_token, csrf_token


def get_auth_service() -> AuthService:
    return AuthService()

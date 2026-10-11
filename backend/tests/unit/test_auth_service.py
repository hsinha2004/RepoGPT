from datetime import UTC, datetime
from typing import Any

import pytest

from app.core.errors import ConflictError, UnauthorizedError
from app.services.auth.service import AuthService


class MockUserRepo:
    def __init__(self) -> None:
        self.users: dict[str, dict[str, Any]] = {}
        self.next_id = 1

    async def get_by_id(self, user_id: str) -> dict[str, Any] | None:
        return self.users.get(user_id)

    async def get_by_email(self, email: str) -> dict[str, Any] | None:
        for u in self.users.values():
            if u["email"] == email.lower():
                return u
        return None

    async def create_user(
        self, email: str, name: str, password_hash: str | None, role: str = "user", _github=None
    ) -> dict[str, Any]:
        uid = f"user_{self.next_id}"
        self.next_id += 1
        doc = {
            "_id": uid,
            "email": email.lower(),
            "name": name,
            "password_hash": password_hash,
            "role": role,
            "is_active": True,
            "failed_login_count": 0,
            "locked_until": None,
            "created_at": datetime.now(UTC),
        }
        self.users[uid] = doc
        return doc

    async def record_login_failure(self, user_id: str, lock_minutes: int = 15) -> tuple[int, bool]:
        user = self.users[user_id]
        user["failed_login_count"] += 1
        is_locked = False
        if user["failed_login_count"] >= 10:
            from datetime import timedelta

            user["locked_until"] = datetime.now(UTC) + timedelta(minutes=lock_minutes)
            is_locked = True
        return user["failed_login_count"], is_locked

    async def record_login_success(self, user_id: str) -> None:
        user = self.users[user_id]
        user["failed_login_count"] = 0
        user["locked_until"] = None

    async def update_password(self, user_id: str, password_hash: str) -> bool:
        self.users[user_id]["password_hash"] = password_hash
        return True


class MockSessionRepo:
    def __init__(self) -> None:
        self.sessions: dict[str, dict[str, Any]] = {}

    async def create_session(
        self,
        user_id: str,
        family_id: str,
        token_hash: str,
        expires_at: datetime,
        user_agent: str = "",
        ip: str = "",
    ) -> dict[str, Any]:
        doc = {
            "user_id": user_id,
            "family_id": family_id,
            "token_hash": token_hash,
            "expires_at": expires_at,
            "user_agent": user_agent,
            "ip": ip,
            "revoked_at": None,
            "replaced_by": None,
        }
        self.sessions[token_hash] = doc
        return doc

    async def get_by_token_hash(self, token_hash: str) -> dict[str, Any] | None:
        return self.sessions.get(token_hash)

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
        self.sessions[old_token_hash]["replaced_by"] = new_token_hash
        self.sessions[old_token_hash]["revoked_at"] = datetime.now(UTC)
        return await self.create_session(
            user_id, family_id, new_token_hash, new_expires_at, user_agent, ip
        )

    async def revoke_family(self, family_id: str) -> int:
        count = 0
        now = datetime.now(UTC)
        for s in self.sessions.values():
            if s["family_id"] == family_id and s["revoked_at"] is None:
                s["revoked_at"] = now
                count += 1
        return count

    async def revoke_token(self, token_hash: str) -> bool:
        if token_hash in self.sessions:
            self.sessions[token_hash]["revoked_at"] = datetime.now(UTC)
            return True
        return False

    async def revoke_all_for_user(self, user_id: str) -> int:
        count = 0
        now = datetime.now(UTC)
        for s in self.sessions.values():
            if s["user_id"] == user_id and s["revoked_at"] is None:
                s["revoked_at"] = now
                count += 1
        return count


class MockAuditRepo:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    async def record_event(
        self, actor_id: str, action: str, target_type: str, target_id: str, **kwargs
    ) -> dict[str, Any]:
        evt = {
            "actor_id": actor_id,
            "action": action,
            "target_type": target_type,
            "target_id": target_id,
            **kwargs,
        }
        self.events.append(evt)
        return evt


@pytest.fixture
def auth_service():
    return AuthService(
        user_repo=MockUserRepo(),  # type: ignore[arg-type]
        session_repo=MockSessionRepo(),  # type: ignore[arg-type]
        audit_repo=MockAuditRepo(),  # type: ignore[arg-type]
    )


@pytest.mark.asyncio
async def test_register_and_login_flow(auth_service: AuthService):
    # 1. Register
    access_token, refresh_token, csrf_token, user = await auth_service.register(
        email="developer@example.com",
        name="Developer Name",
        password="SuperStrongPassword123!",
    )
    assert access_token is not None
    assert refresh_token is not None
    assert csrf_token is not None
    assert user["email"] == "developer@example.com"

    # 2. Duplicate registration fails
    with pytest.raises(ConflictError):
        await auth_service.register(
            email="developer@example.com",
            name="Another",
            password="SuperStrongPassword123!",
        )

    # 3. Login
    acc2, ref2, csrf2, u2 = await auth_service.login(
        email="developer@example.com",
        password="SuperStrongPassword123!",
    )
    assert acc2 is not None
    assert ref2 is not None


@pytest.mark.asyncio
async def test_refresh_token_rotation_and_reuse_detection(auth_service: AuthService):
    # Register to get initial tokens
    _, refresh_token_1, csrf_1, user = await auth_service.register(
        email="rotate@example.com",
        name="Rotate User",
        password="SecurePassphrase123!",
    )

    # First refresh succeeds and rotates
    acc2, refresh_token_2, csrf_2, _ = await auth_service.refresh(
        raw_refresh_token=refresh_token_1,
        csrf_header=csrf_1,
        csrf_cookie=csrf_1,
    )
    assert acc2 is not None
    assert refresh_token_2 != refresh_token_1

    # CSRF mismatch fails
    with pytest.raises(UnauthorizedError):
        await auth_service.refresh(
            raw_refresh_token=refresh_token_2,
            csrf_header="wrong_csrf_header",
            csrf_cookie=csrf_2,
        )

    # Reusing rotated token (token 1) triggers reuse detection & family revocation!
    with pytest.raises(UnauthorizedError) as exc_info:
        await auth_service.refresh(
            raw_refresh_token=refresh_token_1,
            csrf_header=csrf_1,
            csrf_cookie=csrf_1,
        )
    assert "compromised" in str(exc_info.value).lower()

    # Even the new token (token 2) is now revoked because family was compromised!
    with pytest.raises(UnauthorizedError):
        await auth_service.refresh(
            raw_refresh_token=refresh_token_2,
            csrf_header=csrf_2,
            csrf_cookie=csrf_2,
        )


@pytest.mark.asyncio
async def test_account_lockout_after_10_failed_logins(auth_service: AuthService):
    # Register user
    await auth_service.register(
        email="lockout@example.com",
        name="Lockout User",
        password="Password123!Valid",
    )

    # Fail 9 times
    for _ in range(9):
        with pytest.raises(UnauthorizedError):
            await auth_service.login("lockout@example.com", "WrongPassword!")

    # 10th failure triggers lockout
    with pytest.raises(UnauthorizedError) as exc_info:
        await auth_service.login("lockout@example.com", "WrongPassword!")
    assert "locked" in str(exc_info.value).lower()

    # Even with correct password, cannot login while locked
    with pytest.raises(UnauthorizedError) as exc_info2:
        await auth_service.login("lockout@example.com", "Password123!Valid")
    assert "locked" in str(exc_info2.value).lower()

import pytest
from httpx import AsyncClient

from app.api.v1.auth import get_auth_service
from app.core.deps import get_current_user
from app.services.auth.service import AuthService
from tests.unit.test_auth_service import MockAuditRepo, MockSessionRepo, MockUserRepo


@pytest.fixture
def mock_repos():
    user_repo = MockUserRepo()
    session_repo = MockSessionRepo()
    audit_repo = MockAuditRepo()
    auth_service = AuthService(
        user_repo=user_repo, session_repo=session_repo, audit_repo=audit_repo
    )  # type: ignore[arg-type]
    return user_repo, session_repo, audit_repo, auth_service


@pytest.mark.asyncio
async def test_auth_api_full_cycle(client: AsyncClient, app, mock_repos):
    user_repo, session_repo, audit_repo, auth_service = mock_repos
    app.dependency_overrides[get_auth_service] = lambda: auth_service

    # 1. Register
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "alice@example.com",
            "name": "Alice Developer",
            "password": "StrongPassword123!",
        },
    )
    assert reg_res.status_code == 200
    data = reg_res.json()
    assert "access_token" in data
    assert data["user"]["email"] == "alice@example.com"
    assert "rg_refresh" in reg_res.cookies
    assert "rg_csrf" in reg_res.cookies

    access_token = data["access_token"]
    csrf_token = reg_res.cookies["rg_csrf"]

    # 2. Login
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "StrongPassword123!"},
    )
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert "access_token" in login_data
    assert "rg_refresh" in login_res.cookies

    # 3. Authenticated endpoint: /auth/me
    # Override get_current_user to return mock user
    user_doc = await user_repo.get_by_email("alice@example.com")
    app.dependency_overrides[get_current_user] = lambda: user_doc

    me_res = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "alice@example.com"

    # 4. Refresh token
    refresh_res = await client.post(
        "/api/v1/auth/refresh",
        cookies={"rg_refresh": login_res.cookies["rg_refresh"], "rg_csrf": csrf_token},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert refresh_res.status_code == 200
    ref_data = refresh_res.json()
    assert "access_token" in ref_data

    # 5. Logout
    logout_res = await client.post(
        "/api/v1/auth/logout",
        cookies={"rg_refresh": refresh_res.cookies["rg_refresh"]},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert logout_res.status_code == 200
    assert logout_res.json()["message"] == "Successfully logged out"

    app.dependency_overrides.clear()

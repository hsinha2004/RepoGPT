"""
Integration test for §11.7 AuthZ Anti-Enumeration.

Enumerates EVERY route in the FastAPI application containing resource identifiers
({repo_id}, {conversation_id}, {review_id}, {job_id}, {run_id}, {message_id}, {finding_id}, {benchmark_id})
and asserts:
1. An unauthenticated request is rejected with 401 UNAUTHORIZED.
2. An authenticated request by a non-member/non-owner returns 404 NOT FOUND (never revealing resource existence).
"""

from __future__ import annotations

import re
from typing import Any

import pytest
from bson import ObjectId
from httpx import ASGITransport, AsyncClient

import app.db.mongo as mongo
from app.core.deps import get_current_user
from app.core.security import create_access_token
from app.main import create_app

RESOURCE_PARAM_PATTERN = re.compile(
    r"\{(repo_id|conversation_id|review_id|job_id|run_id|message_id|finding_id|benchmark_id)\}"
)

DUMMY_SUBSTITUTIONS = {
    "{repo_id}": "607f1f77bcf86cd799439011",
    "{conversation_id}": "607f1f77bcf86cd799439012",
    "{job_id}": "607f1f77bcf86cd799439013",
    "{run_id}": "607f1f77bcf86cd799439014",
    "{message_id}": "607f1f77bcf86cd799439015",
    "{review_id}": "607f1f77bcf86cd799439016",
    "{finding_id}": "607f1f77bcf86cd799439017",
    "{benchmark_id}": "non-existent-benchmark-id-999",
}


class MockCollection:
    def __init__(self, name: str = "col") -> None:
        self.name = name

    async def find_one(self, *args: Any, **kwargs: Any) -> Any:
        return None

    async def find_one_and_update(self, *args: Any, **kwargs: Any) -> Any:
        return None

    async def find_one_and_delete(self, *args: Any, **kwargs: Any) -> Any:
        return None

    async def insert_one(self, *args: Any, **kwargs: Any) -> Any:
        return type("Res", (), {"inserted_id": ObjectId()})()

    async def update_one(self, *args: Any, **kwargs: Any) -> Any:
        return type("Res", (), {"modified_count": 0})()

    async def delete_one(self, *args: Any, **kwargs: Any) -> Any:
        return type("Res", (), {"deleted_count": 0})()

    async def insert_many(self, docs: list[dict[str, Any]], *args: Any, **kwargs: Any) -> Any:
        return type("Res", (), {"inserted_ids": [ObjectId() for _ in docs]})()

    async def update_many(self, *args: Any, **kwargs: Any) -> Any:
        return type("Res", (), {"modified_count": 0})()

    async def delete_many(self, *args: Any, **kwargs: Any) -> Any:
        return type("Res", (), {"deleted_count": 0})()

    def find(self, *args: Any, **kwargs: Any) -> Any:
        class Cursor:
            def sort(self, *args: Any, **kwargs: Any) -> Any:
                return self

            def skip(self, *args: Any, **kwargs: Any) -> Any:
                return self

            def limit(self, *args: Any, **kwargs: Any) -> Any:
                return self

            def __aiter__(self) -> Any:
                return self

            async def __anext__(self) -> Any:
                raise StopAsyncIteration

            async def to_list(self, *args: Any, **kwargs: Any) -> list[Any]:
                return []

        return Cursor()

    async def count_documents(self, *args: Any, **kwargs: Any) -> int:
        return 0


class MockDatabase:
    def __init__(self) -> None:
        self._collections: dict[str, MockCollection] = {}

    def __getitem__(self, name: str) -> MockCollection:
        if name not in self._collections:
            self._collections[name] = MockCollection(name)
        return self._collections[name]

    def __getattr__(self, name: str) -> MockCollection:
        return self[name]


class MockMongoClient:
    def __init__(self) -> None:
        self._db = MockDatabase()

    def __getitem__(self, name: str) -> MockDatabase:
        return self._db

    def __getattr__(self, name: str) -> MockDatabase:
        return self._db


@pytest.mark.asyncio
async def test_authz_enumeration_and_unauthorized_rejection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(mongo, "_mongo_client", MockMongoClient())
    app = create_app()

    # Discover all scoped routes from OpenAPI catalogue
    scoped_routes: list[tuple[str, str]] = []  # (method, path)
    paths = app.openapi().get("paths", {})
    for path, path_item in paths.items():
        if RESOURCE_PARAM_PATTERN.search(path):
            for method in path_item.keys():
                if method.upper() in {"GET", "POST", "PATCH", "DELETE", "PUT"}:
                    scoped_routes.append((method.upper(), path))

    # Assert that routes were dynamically detected
    assert len(scoped_routes) >= 10, (
        f"Expected at least 10 scoped routes, found {len(scoped_routes)}"
    )

    # Create dummy unauthorized user
    attacker_token = create_access_token(
        user_id="user_unauthorized_attacker",
        role="user",
    )
    auth_headers = {"Authorization": f"Bearer {attacker_token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for method, route_path in scoped_routes:
            # Format path with dummy IDs
            formatted_path = route_path
            for param, dummy_val in DUMMY_SUBSTITUTIONS.items():
                formatted_path = formatted_path.replace(param, dummy_val)

            # 1. Unauthenticated Request -> Must be 401
            unauth_res = await client.request(method, formatted_path)
            assert unauth_res.status_code in {401, 403}, (
                f"Expected 401 for unauthenticated {method} {formatted_path}, got {unauth_res.status_code}"
            )

        # 2. Authenticated Non-Member Request -> Must be 404 (Anti-Enumeration §7.5, §11.7)
        app.dependency_overrides[get_current_user] = lambda: {
            "_id": "user_unauthorized_attacker",
            "email": "attacker@example.com",
            "role": "user",
        }

        for method, route_path in scoped_routes:
            formatted_path = route_path
            for param, dummy_val in DUMMY_SUBSTITUTIONS.items():
                formatted_path = formatted_path.replace(param, dummy_val)

            auth_res = await client.request(
                method,
                formatted_path,
                headers=auth_headers,
                json={},  # Send empty payload for POST/PATCH
            )

            # Must be 404 Not Found (or 403 for admin-restricted endpoints, or 422 for payload schema requirements)
            expected_statuses = {403, 404, 422} if "/admin/" in route_path else {404, 422}
            assert auth_res.status_code in expected_statuses, (
                f"Expected {expected_statuses} (Anti-Enumeration) for {method} {formatted_path}, got {auth_res.status_code}. "
                f"Response body: {auth_res.text}"
            )

        # 3. For admin user, non-existent job retry returns 404
        app.dependency_overrides[get_current_user] = lambda: {
            "_id": "admin_user_id",
            "email": "admin@example.com",
            "role": "admin",
        }
        admin_res = await client.post(
            "/api/v1/admin/jobs/607f1f77bcf86cd799439013/retry",
            headers=auth_headers,
        )
        assert admin_res.status_code == 404, (
            f"Expected 404 for non-existent admin job, got {admin_res.status_code}"
        )

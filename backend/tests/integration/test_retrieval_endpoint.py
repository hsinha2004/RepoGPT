from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.repos import (
    get_member_repository,
    get_repo_repository,
    get_retrieval_service,
)
from app.core.deps import get_current_user
from app.main import create_app
from app.schemas.retrieval import (
    RouteResult,
    RouterEnrich,
    RouterWeights,
    SearchResponse,
)


class MockRepoRepo:
    def __init__(self, repos: dict | None = None) -> None:
        self.repos = repos or {}

    async def get_by_id(self, repo_id: str):
        return self.repos.get(repo_id)


class MockMemberRepo:
    async def get_member(self, repo_id: str, user_id: str):
        return None


@pytest.fixture
def test_app():
    app = create_app()
    mock_repos = MockRepoRepo()
    mock_members = MockMemberRepo()
    mock_retrieval = MagicMock()
    mock_retrieval.search = AsyncMock()

    app.dependency_overrides[get_current_user] = lambda: {
        "_id": "507f1f77bcf86cd799439011",
        "email": "test@example.com",
        "role": "admin",
    }
    app.dependency_overrides[get_repo_repository] = lambda: mock_repos
    app.dependency_overrides[get_member_repository] = lambda: mock_members
    app.dependency_overrides[get_retrieval_service] = lambda: mock_retrieval
    return app, mock_repos, mock_retrieval


@pytest.mark.asyncio
async def test_search_endpoint_unauthorized() -> None:
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/repos/nonexistent/search",
            json={"query": "test query"},
        )
        assert res.status_code == 401


@pytest.mark.asyncio
async def test_search_endpoint_not_found(test_app) -> None:
    app, _mock_repos, _ = test_app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/repos/507f1f77bcf86cd799439011/search",
            json={"query": "test query"},
            headers={"Authorization": "Bearer fake_token"},
        )
        assert res.status_code == 404
        body = res.json()
        assert "error" in body
        assert body["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_search_endpoint_validation_error(test_app) -> None:
    app, _mock_repos, _ = test_app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/repos/507f1f77bcf86cd799439011/search",
            json={"query": ""},
            headers={"Authorization": "Bearer fake_token"},
        )
        assert res.status_code == 422


@pytest.mark.asyncio
async def test_search_endpoint_success(test_app) -> None:
    app, mock_repos, mock_retrieval = test_app
    repo_id = "507f1f77bcf86cd799439011"
    mock_repos.repos[repo_id] = {
        "_id": repo_id,
        "name": "sample-repo",
        "owner_id": "507f1f77bcf86cd799439011",
    }

    mock_response = SearchResponse(
        query="find router function",
        route=RouteResult(
            intent="locate",
            strategy="hybrid_rerank",
            weights=RouterWeights(bm25=0.5, vector=0.5),
            enrich=RouterEnrich(),
            reason="Query seeks code function",
        ),
        results=[],
        context="<retrieved_context></retrieved_context>",
        total_candidates=0,
        latency_ms={"total": 15.2},
    )
    mock_retrieval.search.return_value = mock_response

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            f"/api/v1/repos/{repo_id}/search",
            json={"query": "find router function"},
            headers={"Authorization": "Bearer fake_token"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["query"] == "find router function"
        assert data["route"]["intent"] == "locate"
        assert data["context"] == "<retrieved_context></retrieved_context>"
        assert data["results"] == []

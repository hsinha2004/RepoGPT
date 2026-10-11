import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_live_health_endpoint(client: AsyncClient):
    response = await client.get("/api/v1/health/live")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "RepoGPT"
    assert data["version"] == "0.1.0"
    assert "X-Request-ID" in response.headers
    assert response.headers["X-Content-Type-Options"] == "nosniff"


@pytest.mark.asyncio
async def test_ready_health_endpoint(client: AsyncClient):
    response = await client.get("/api/v1/health/ready")
    assert response.status_code in (200, 503)
    data = response.json()
    assert "components" in data
    assert "mongodb" in data["components"]
    assert "redis" in data["components"]
    assert "vector_store" in data["components"]
    assert "llm" in data["components"]

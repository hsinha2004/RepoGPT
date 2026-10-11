"""
Pytest global fixtures and configuration.
"""

import os

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings
from app.main import create_app

# Force test environment
os.environ["ENVIRONMENT"] = "test"
os.environ["JWT_SECRET"] = (
    "test-secret-key-that-has-at-least-64-bytes-for-hmac-sha256-signing-repogpt"
)
os.environ["ENCRYPTION_KEY"] = "MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTIzNDU2Nzg5MDE="
os.environ["LLM_PROVIDER"] = "fake"
os.environ["EMBEDDING_PROVIDER"] = "fake"
os.environ["RERANKER_PROVIDER"] = "fake"


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture
def app():
    get_settings.cache_clear()
    return create_app()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c

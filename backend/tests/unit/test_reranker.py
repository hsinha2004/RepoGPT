import pytest
from app.core.config import Settings
from app.services.retrieval.reranker.factory import get_reranker_provider
from app.services.retrieval.reranker.fake import FakeRerankerProvider
from app.services.retrieval.reranker.fastembed_reranker import FastEmbedRerankerProvider


@pytest.mark.asyncio
async def test_fake_reranker_provider_scoring() -> None:
    provider = FakeRerankerProvider()
    query = "AuthService login"
    texts = [
        "class AuthService:\n    def login(self, email, password):\n        return token",
        "def unrelated_helper_function():\n    return 42",
        "",
    ]

    scores = await provider.rerank(query, texts)
    assert len(scores) == 3
    # First text has AuthService and login -> should score highest
    assert scores[0] > scores[1]
    assert all(0.0 <= s <= 1.0 for s in scores)

    # Empty list handling
    empty_scores = await provider.rerank(query, [])
    assert empty_scores == []


@pytest.mark.asyncio
async def test_reranker_factory() -> None:
    fake_settings = Settings(RERANKER_PROVIDER="fake")
    provider = get_reranker_provider(fake_settings)
    assert isinstance(provider, FakeRerankerProvider)

    # Singleton caching
    provider_2 = get_reranker_provider(fake_settings)
    assert provider is provider_2


@pytest.mark.asyncio
async def test_fastembed_reranker_provider() -> None:
    # Test using FastEmbed provider (model downloaded during M4/M5 setup)
    provider = FastEmbedRerankerProvider(
        model_name="Xenova/ms-marco-MiniLM-L-6-v2",
    )
    query = "JWT access token expiration"
    texts = [
        "def create_access_token(data: dict, expires_delta: timedelta):\n    to_encode = data.copy()",
        "HTML button styling and padding: background-color #fff",
    ]

    scores = await provider.rerank(query, texts)
    assert len(scores) == 2
    assert scores[0] > scores[1]
    assert all(0.0 <= s <= 1.0 for s in scores)

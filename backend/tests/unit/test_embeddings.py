"""
Unit tests for Embedding Providers and EmbeddingCache (§8.6).
"""

import math

import pytest

from app.services.indexing.embeddings.cache import EmbeddingCache
from app.services.indexing.embeddings.factory import get_embedding_provider
from app.services.indexing.embeddings.fake import FakeEmbeddingProvider


def test_fake_embedding_provider_shape_and_normalization():
    provider = FakeEmbeddingProvider()
    assert provider.name == "fake"
    assert provider.dim == 256

    texts = [
        "def getUserById(userId: str) -> UserProfile:",
        "class AuthService: pass",
        "import fastapi",
    ]
    vectors = provider.embed_documents(texts)
    assert len(vectors) == 3

    for vec in vectors:
        assert len(vec) == 256
        # Verify L2 normalization: norm ≈ 1.0
        norm = math.sqrt(sum(x * x for x in vec))
        assert abs(norm - 1.0) < 1e-4

    # Query embedding
    q_vec = provider.embed_query("getUserById")
    assert len(q_vec) == 256
    q_norm = math.sqrt(sum(x * x for x in q_vec))
    assert abs(q_norm - 1.0) < 1e-4


def test_fake_embedding_provider_determinism():
    provider = FakeEmbeddingProvider()
    text = "const apiClient = axios.create();"

    v1 = provider.embed_documents([text])[0]
    v2 = provider.embed_documents([text])[0]
    v3 = provider.embed_query(text)

    # Must be 100% deterministic
    assert v1 == v2
    assert v1 == v3

    # Different text must yield different vectors
    v_diff = provider.embed_query("completely different string")
    assert v1 != v_diff


def test_embedding_factory_resolution():
    p_fake = get_embedding_provider("fake")
    assert isinstance(p_fake, FakeEmbeddingProvider)
    assert p_fake.dim == 256

    p_default = get_embedding_provider("nonexistent_provider")
    assert isinstance(p_default, FakeEmbeddingProvider)


@pytest.mark.asyncio
async def test_embedding_cache_fallback():
    # Cache without active Mongo should gracefully return empty dict and not crash
    cache = EmbeddingCache(collection=None)

    res = await cache.get_cached_embeddings("fake-model", ["hash1", "hash2"])
    assert res == {}

    # Saving to disconnected cache should not raise
    await cache.save_embeddings("fake-model", [("hash1", [0.1] * 256)])

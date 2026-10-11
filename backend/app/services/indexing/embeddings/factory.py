"""
Factory for instantiating Embedding Providers (§8.6).
"""

from app.core.config import get_settings
from app.services.indexing.embeddings.api import APIEmbeddingProvider
from app.services.indexing.embeddings.base import EmbeddingProvider
from app.services.indexing.embeddings.fake import FakeEmbeddingProvider
from app.services.indexing.embeddings.fastembed_provider import FastEmbedProvider


def get_embedding_provider(
    provider_name: str | None = None,
    model_name: str | None = None,
    model: str | None = None,
) -> EmbeddingProvider:
    settings = get_settings()
    p_name = (provider_name or settings.EMBEDDING_PROVIDER).lower()
    m_name = model or model_name or settings.EMBEDDING_MODEL

    if p_name == "fake":
        return FakeEmbeddingProvider()
    elif p_name == "fastembed":
        return FastEmbedProvider(model_name=m_name)
    elif p_name in ("openai", "gemini", "voyage"):
        return APIEmbeddingProvider(provider_name=p_name, model_name=m_name)

    return FakeEmbeddingProvider()

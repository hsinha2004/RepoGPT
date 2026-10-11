"""
Embeddings package (§8.6).
"""

from app.services.indexing.embeddings.base import EmbeddingProvider
from app.services.indexing.embeddings.cache import EmbeddingCache
from app.services.indexing.embeddings.factory import get_embedding_provider
from app.services.indexing.embeddings.fake import FakeEmbeddingProvider
from app.services.indexing.embeddings.fastembed_provider import FastEmbedProvider

__all__ = [
    "EmbeddingProvider",
    "FakeEmbeddingProvider",
    "FastEmbedProvider",
    "EmbeddingCache",
    "get_embedding_provider",
]

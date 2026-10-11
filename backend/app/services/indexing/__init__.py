"""
Indexing subsystem: embeddings, vector stores, BM25 keyword index, and sync (§8.6, §8.7, §8.10).
"""

from app.services.indexing.bm25 import BM25Index, BM25IndexManager, BM25Match, get_bm25_manager
from app.services.indexing.embeddings import (
    EmbeddingCache,
    EmbeddingProvider,
    get_embedding_provider,
)
from app.services.indexing.sync import IncrementalSyncService, RepoDeletionService
from app.services.indexing.vector import VectorMatch, VectorStore, get_vector_store

__all__ = [
    "EmbeddingProvider",
    "EmbeddingCache",
    "get_embedding_provider",
    "VectorStore",
    "VectorMatch",
    "get_vector_store",
    "BM25Index",
    "BM25IndexManager",
    "BM25Match",
    "get_bm25_manager",
    "IncrementalSyncService",
    "RepoDeletionService",
]

"""
Vector stores package (§6.3).
"""

from app.services.indexing.vector.base import VectorMatch, VectorStore
from app.services.indexing.vector.chroma import ChromaVectorStore
from app.services.indexing.vector.factory import get_vector_store
from app.services.indexing.vector.faiss_store import FAISSVectorStore

__all__ = [
    "VectorStore",
    "VectorMatch",
    "ChromaVectorStore",
    "FAISSVectorStore",
    "get_vector_store",
]

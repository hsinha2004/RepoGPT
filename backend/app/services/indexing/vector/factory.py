"""
Factory for instantiating VectorStore (§6.3).
"""

from app.core.config import get_settings
from app.services.indexing.vector.base import VectorStore
from app.services.indexing.vector.chroma import ChromaVectorStore
from app.services.indexing.vector.faiss_store import FAISSVectorStore


def get_vector_store(
    repo_id: str,
    model_slug: str,
    store_type: str | None = None,
) -> VectorStore:
    settings = get_settings()
    s_type = (store_type or settings.VECTOR_STORE).lower()

    if s_type == "faiss":
        return FAISSVectorStore(repo_id=repo_id, model_slug=model_slug)

    return ChromaVectorStore(repo_id=repo_id, model_slug=model_slug)

from __future__ import annotations

from typing import Any

import anyio
import structlog

from app.core.config import Settings
from app.services.indexing.embeddings.cache import EmbeddingCache
from app.services.indexing.embeddings.factory import get_embedding_provider
from app.services.indexing.vector.factory import get_vector_store

logger = structlog.get_logger(__name__)


class VectorSearchService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.embedding_cache = EmbeddingCache()

    async def search(
        self,
        repo_id: str,
        embedding_model: str,
        query: str,
        k: int = 50,
        chunk_type_filter: str | None = None,
    ) -> list[tuple[str, int, float]]:
        """Embeds query and executes vector similarity search against the repo's vector index.

        Returns a list of (chunk_id, rank_1_indexed, similarity_score).
        """
        if not query.strip():
            return []

        # 1. Get or compute query embedding
        query_vector = await self.embedding_cache.get_cached_query_vector(
            model=embedding_model,
            query=query,
        )
        if query_vector is None:
            provider = get_embedding_provider(model=embedding_model)
            query_vector = await anyio.to_thread.run_sync(provider.embed_query, query)
            await self.embedding_cache.cache_query_vector(
                model=embedding_model,
                query=query,
                vector=query_vector,
            )

        # 2. Get vector store
        store = get_vector_store(
            repo_id=repo_id,
            model_slug=embedding_model,
        )

        where: dict[str, Any] | None = None
        if chunk_type_filter:
            where = {"chunk_type": chunk_type_filter}

        # 3. Query store
        try:
            results = await anyio.to_thread.run_sync(store.query, query_vector, k, where)
        except Exception as e:
            logger.warning("vector_store_query_failed", repo_id=repo_id, error=str(e))
            return []

        ranked: list[tuple[str, int, float]] = []
        for i, item in enumerate(results, start=1):
            ranked.append((item.id, i, item.score))
        return ranked

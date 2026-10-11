from __future__ import annotations

import structlog

from app.core.config import Settings
from app.services.keyword.bm25_index import get_bm25_index_manager

logger = structlog.get_logger(__name__)


class KeywordSearchService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.bm25_manager = get_bm25_index_manager()

    async def search(
        self,
        repo_id: str,
        commit_sha: str,
        query: str,
        k: int = 50,
    ) -> list[tuple[str, int, float]]:
        """Performs BM25 keyword search against the repository snapshot index.

        Returns a list of (chunk_id, rank_1_indexed, bm25_score).
        """
        if not query.strip():
            return []

        index = self.bm25_manager.get_index(repo_id=repo_id, commit_sha=commit_sha)
        if index is None or index.doc_count == 0:
            logger.warning(
                "bm25_index_not_found_or_empty",
                repo_id=repo_id,
                commit_sha=commit_sha,
            )
            return []

        results = index.search(query=query, k=k)
        ranked: list[tuple[str, int, float]] = []
        for i, item in enumerate(results, start=1):
            ranked.append((item.chunk_id, i, item.score))
        return ranked

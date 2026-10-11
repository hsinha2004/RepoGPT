from __future__ import annotations

from typing import Any

from app.db.repositories.chunks import ChunkRepository
from app.db.repositories.files import FileRepository


class SummaryScopeService:
    def __init__(
        self,
        chunk_repo: ChunkRepository,
        file_repo: FileRepository,
    ) -> None:
        self.chunk_repo = chunk_repo
        self.file_repo = file_repo

    async def get_summary_candidates(
        self,
        repo_id: str,
        limit: int = 25,
    ) -> list[tuple[str, int, dict[str, Any]]]:
        """Collects architecture and high-level summary chunks.

        Order of priority:
        1. Overview chunks
        2. Directory summaries
        3. Top PageRank file cards
        4. Documentation chunks
        """
        seen_ids: set[str] = set()
        candidates: list[tuple[str, int, dict[str, Any]]] = []
        current_rank = 1

        def add_chunk(chunk: dict[str, Any]) -> None:
            nonlocal current_rank
            cid = str(chunk.get("_id") or chunk.get("chunk_id"))
            if cid and cid not in seen_ids:
                seen_ids.add(cid)
                candidates.append((cid, current_rank, chunk))
                current_rank += 1

        # 1. Overview chunks
        overview_chunks = await self.chunk_repo.list_for_repo(
            repo_id=repo_id,
            chunk_type="overview",
            limit=5,
        )
        for c in overview_chunks:
            add_chunk(c)

        # 2. Directory summaries
        dir_chunks = await self.chunk_repo.list_for_repo(
            repo_id=repo_id,
            chunk_type="dir_summary",
            limit=10,
        )
        for c in dir_chunks:
            add_chunk(c)

        # 3. Top PageRank file cards
        top_files = await self.file_repo.list_top_pagerank_files(repo_id=repo_id, limit=15)
        top_paths = [str(f["path"]) for f in top_files if f.get("path")]
        if top_paths:
            pagerank_chunks = await self.chunk_repo.get_chunks_for_files(
                repo_id=repo_id,
                paths=top_paths,
            )
            for c in pagerank_chunks:
                if c.get("chunk_type") == "file_card":
                    add_chunk(c)

        # 4. General file cards if not enough
        if len(candidates) < limit:
            file_cards = await self.chunk_repo.list_for_repo(
                repo_id=repo_id,
                chunk_type="file_card",
                limit=limit - len(candidates),
            )
            for c in file_cards:
                add_chunk(c)

        # 5. Documentation chunks
        if len(candidates) < limit:
            doc_chunks = await self.chunk_repo.list_for_repo(
                repo_id=repo_id,
                chunk_type="doc",
                limit=limit - len(candidates),
            )
            for c in doc_chunks:
                add_chunk(c)

        return candidates[:limit]

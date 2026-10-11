from __future__ import annotations

from typing import Any

from app.db.repositories.chunks import ChunkRepository
from app.db.repositories.graph import GraphRepository


class GraphExpansionService:
    def __init__(
        self,
        graph_repo: GraphRepository,
        chunk_repo: ChunkRepository,
    ) -> None:
        self.graph_repo = graph_repo
        self.chunk_repo = chunk_repo

    async def expand(
        self,
        repo_id: str,
        top_file_paths: list[str],
        max_candidates: int = 10,
    ) -> list[tuple[str, int, dict[str, Any]]]:
        """Expands candidates via 1-hop graph neighbors (imports and incoming imports/calls).

        Returns a list of (chunk_id, rank, chunk_doc).
        """
        if not top_file_paths:
            return []

        # Take up to top 5 files
        seed_paths = top_file_paths[:5]
        edges = await self.graph_repo.get_neighbors(repo_id=repo_id, paths=seed_paths)

        neighbor_paths: set[str] = set()
        for edge in edges:
            src = edge.get("source", "")
            tgt = edge.get("target", "")

            # If seed was source, add internal target
            if src in seed_paths and tgt and not tgt.startswith("ext:") and tgt not in seed_paths:
                neighbor_paths.add(tgt)
            # If seed was target, add internal source
            if tgt in seed_paths and src and not src.startswith("ext:") and src not in seed_paths:
                neighbor_paths.add(src)

        if not neighbor_paths:
            return []

        # Fetch chunks for these neighbor files (prioritize module_header, class_skeleton, and symbol chunks)
        neighbor_chunks = await self.chunk_repo.get_chunks_for_files(
            repo_id=repo_id,
            paths=list(neighbor_paths),
        )

        results: list[tuple[str, int, dict[str, Any]]] = []
        for i, c in enumerate(neighbor_chunks[:max_candidates], start=1):
            cid = str(c.get("_id") or c.get("chunk_id"))
            results.append((cid, i, c))

        return results

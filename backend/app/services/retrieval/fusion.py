from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.schemas.retrieval import RankScores


@dataclass
class FusedCandidate:
    chunk_id: str
    rrf_score: float = 0.0
    ranks: RankScores = field(default_factory=RankScores)
    bm25_score: float | None = None
    vector_score: float | None = None
    raw_doc: dict | None = None


def reciprocal_rank_fusion(
    bm25_results: list[tuple[str, int, float]] | None = None,
    vector_results: list[tuple[str, int, float]] | None = None,
    symbol_results: list[tuple[Any, ...]] | None = None,
    graph_results: list[tuple[Any, ...]] | None = None,
    summary_results: list[tuple[Any, ...]] | None = None,
    *,
    rrf_k: int = 60,
    bm25_weight: float = 0.5,
    vector_weight: float = 0.5,
    symbol_weight: float = 1.0,
    graph_weight: float = 0.8,
    summary_weight: float = 0.7,
) -> list[FusedCandidate]:
    """Combines candidate lists from multiple retrieval sources using weighted Reciprocal Rank Fusion.

    score(d) = sum_s w_s / (rrf_k + rank_s(d))
    """
    candidates: dict[str, FusedCandidate] = {}

    def get_candidate(cid: str) -> FusedCandidate:
        if cid not in candidates:
            candidates[cid] = FusedCandidate(chunk_id=cid)
        return candidates[cid]

    # 1. BM25 results: (chunk_id, rank, score)
    if bm25_results:
        for cid, rank, score in bm25_results:
            c = get_candidate(cid)
            c.ranks.bm25 = rank
            c.bm25_score = score
            c.rrf_score += bm25_weight / (rrf_k + rank)

    # 2. Vector results: (chunk_id, rank, score)
    if vector_results:
        for cid, rank, score in vector_results:
            c = get_candidate(cid)
            c.ranks.vector = rank
            c.vector_score = score
            c.rrf_score += vector_weight / (rrf_k + rank)

    # 3. Symbol lookup results: (chunk_id, rank, doc/info)
    if symbol_results:
        for item in symbol_results:
            cid = item[0]
            rank = item[1]
            c = get_candidate(cid)
            c.ranks.symbol = rank
            c.rrf_score += symbol_weight / (rrf_k + rank)
            if len(item) > 2 and isinstance(item[2], dict) and c.raw_doc is None:
                c.raw_doc = item[2]

    # 4. Graph expansion results: (chunk_id, rank, doc)
    if graph_results:
        for item in graph_results:
            cid = item[0]
            rank = item[1]
            c = get_candidate(cid)
            c.ranks.graph = rank
            c.rrf_score += graph_weight / (rrf_k + rank)
            if len(item) > 2 and isinstance(item[2], dict) and c.raw_doc is None:
                c.raw_doc = item[2]

    # 5. Summary scope results: (chunk_id, rank, doc)
    if summary_results:
        for item in summary_results:
            cid = item[0]
            rank = item[1]
            c = get_candidate(cid)
            c.rrf_score += summary_weight / (rrf_k + rank)
            if len(item) > 2 and isinstance(item[2], dict) and c.raw_doc is None:
                c.raw_doc = item[2]

    # Sort descending by fused score
    sorted_candidates = sorted(candidates.values(), key=lambda x: x.rrf_score, reverse=True)
    return sorted_candidates

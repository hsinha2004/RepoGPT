from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

RouterIntent = Literal[
    "locate",
    "explain",
    "flow",
    "architecture",
    "dependency",
    "config",
    "general",
    "out_of_scope",
]

RetrievalStrategy = Literal[
    "auto",
    "keyword",
    "vector",
    "hybrid",
    "hybrid_rerank",
]


class RouterWeights(BaseModel):
    bm25: float = Field(default=0.5, ge=0.0, le=1.0)
    vector: float = Field(default=0.5, ge=0.0, le=1.0)


class RouterEnrich(BaseModel):
    symbol_lookup: bool = Field(default=True)
    graph_expand: bool = Field(default=False)
    summary_scope: bool = Field(default=False)


class RouteResult(BaseModel):
    intent: RouterIntent
    strategy: RetrievalStrategy
    weights: RouterWeights = Field(default_factory=RouterWeights)
    enrich: RouterEnrich = Field(default_factory=RouterEnrich)
    identifiers: list[str] = Field(default_factory=list)
    search_queries: list[str] = Field(default_factory=list)
    reason: str = Field(max_length=250)


class RankScores(BaseModel):
    bm25: int | None = None
    vector: int | None = None
    symbol: int | None = None
    graph: int | None = None


class RetrievedChunk(BaseModel):
    chunk_id: str
    repo_id: str
    commit_sha: str
    path: str
    language: str
    chunk_type: str
    symbol_name: str | None = None
    symbol_kind: str | None = None
    parent_symbol: str | None = None
    start_line: int
    end_line: int
    part: int = 1
    parts: int = 1
    text: str
    embed_text: str
    token_count: int
    score: float = 0.0
    ranks: RankScores = Field(default_factory=RankScores)
    rerank_score: float | None = None


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    strategy: RetrievalStrategy = "auto"
    top_k: int = Field(default=8, ge=1, le=50)
    file_pattern: str | None = None
    language: str | None = None


class SearchResponse(BaseModel):
    query: str
    route: RouteResult
    results: list[RetrievedChunk]
    context: str
    total_candidates: int
    latency_ms: dict[str, float] = Field(default_factory=dict)

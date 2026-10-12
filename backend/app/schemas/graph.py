from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class GraphNode(BaseModel):
    id: str
    label: str
    full_path: str
    is_external: bool = False
    top_directory: str = "root"
    fan_in: int = 0
    fan_out: int = 0
    pagerank: float = 0.0
    in_cycle: bool = False
    is_orphan: bool = False
    file_count: int | None = None


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    type: Literal["imports", "calls"] = "imports"
    heuristic: bool = False
    symbol: str | None = None
    weight: int = 1


class GraphResponse(BaseModel):
    level: Literal["file", "directory"] = "file"
    depth: int | None = None
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
    cycles: list[list[str]] = Field(default_factory=list)
    total_nodes: int = 0
    total_edges: int = 0
    orphan_count: int = 0


class RepoStatsResponse(BaseModel):
    repo_id: str
    commit_sha: str | None = None
    total_files: int = 0
    total_loc: int = 0
    total_symbols: int = 0
    total_chunks: int = 0
    total_redactions: int = 0
    languages: dict[str, int] = Field(default_factory=dict)
    file_counts_by_kind: dict[str, int] = Field(default_factory=dict)

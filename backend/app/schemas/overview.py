from __future__ import annotations

from pydantic import BaseModel, Field


class TechStackItem(BaseModel):
    name: str
    category: str  # framework | database | testing | infra | language
    evidence: str


class EntryPointItem(BaseModel):
    path: str
    kind: str
    description: str
    line: int = 1


class ReadingOrderItem(BaseModel):
    step: int
    path: str
    category: str
    reason: str


class OverviewSourceItem(BaseModel):
    id: str
    path: str
    start_line: int = 1
    end_line: int = 1
    symbol: str | None = None
    snippet: str = ""


class OverviewResponse(BaseModel):
    repo_id: str
    commit_sha: str | None = None
    markdown: str
    suggested_questions: list[str] = Field(default_factory=list)
    tech_stack: list[TechStackItem] = Field(default_factory=list)
    entry_points: list[EntryPointItem] = Field(default_factory=list)
    reading_order: list[ReadingOrderItem] = Field(default_factory=list)
    sources: list[OverviewSourceItem] = Field(default_factory=list)
    updated_at: str | None = None

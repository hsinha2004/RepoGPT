from __future__ import annotations

from typing import Any, TypedDict


class QAState(TypedDict, total=False):
    """Execution state for the LangGraph QA Agentic Workflow (§9.3)."""

    repo_id: str
    commit_sha: str
    user_id: str
    repo_full_name: str
    languages: str
    question: str
    standalone_question: str
    history: list[dict[str, str]]
    strategy_override: str | None

    # Routing
    route: dict[str, Any]
    queries: list[str]

    # Retrieval & Reranking
    candidates: list[dict[str, Any]]
    context: str
    sources_map: dict[str, dict[str, Any]]
    attempt: int
    insufficient: bool

    # Generation & Verification
    answer: str
    cleaned_answer: str
    citations: list[dict[str, Any]]
    removed_citations: list[str]
    confidence: dict[str, Any]
    usage: dict[str, Any]
    timings: dict[str, float]
    trace: dict[str, Any]
    events: list[dict[str, Any]]

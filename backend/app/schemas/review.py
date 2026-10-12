"""
Pydantic schemas for Phase 2: Context-Aware Code Review (§10, §12.6).
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class FindingEvidence(BaseModel):
    source_id: str
    path: str
    start_line: int
    end_line: int


class ReviewFinding(BaseModel):
    id: str
    path: str
    start_line: int
    end_line: int
    side: Literal["LEFT", "RIGHT"] = "RIGHT"
    category: Literal[
        "bug",
        "security",
        "performance",
        "error_handling",
        "concurrency",
        "api_contract",
        "testing",
        "maintainability",
        "documentation",
    ]
    severity: Literal["critical", "high", "medium", "low", "info"]
    title: str = Field(..., max_length=80)
    explanation: str
    suggestion: str | None = None
    suggested_code: str | None = None
    evidence: list[FindingEvidence] = Field(default_factory=list)
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    origin: Literal["llm", "static"] = "llm"
    status: Literal["pending", "accepted", "rejected", "edited"] = "pending"
    user_note: str | None = None


class ReviewFindingUpdate(BaseModel):
    status: Literal["pending", "accepted", "rejected", "edited"] | None = None
    severity: Literal["critical", "high", "medium", "low", "info"] | None = None
    title: str | None = Field(None, max_length=80)
    explanation: str | None = None
    suggestion: str | None = None
    suggested_code: str | None = None
    user_note: str | None = None


class ReviewSource(BaseModel):
    type: Literal["github", "upload", "webhook"]
    pr_number: int | None = None
    pr_url: str | None = None
    base_sha: str | None = None
    head_sha: str | None = None
    patch_filename: str | None = None


class ReviewStats(BaseModel):
    files_changed: int = 0
    lines_added: int = 0
    lines_deleted: int = 0
    findings_count: int = 0
    accepted_count: int = 0
    rejected_count: int = 0


class ReviewCreateGitHub(BaseModel):
    pr_url: str = Field(..., description="GitHub pull request URL (e.g. https://github.com/owner/repo/pull/123)")


class ReviewResponse(BaseModel):
    id: str
    repo_id: str
    user_id: str
    source: ReviewSource
    status: Literal["pending", "running", "completed", "failed"]
    risk_level: Literal["low", "medium", "high", "critical"] = "low"
    stats: ReviewStats
    summary: str = ""
    file_walkthrough: list[dict[str, Any]] = Field(default_factory=list)
    findings: list[ReviewFinding] = Field(default_factory=list)
    general_comments: list[dict[str, Any]] = Field(default_factory=list)
    published_to_github: bool = False
    github_review_id: str | None = None
    github_review_url: str | None = None
    error: str | None = None
    indexed_commit_mismatch: bool = False
    created_at: str
    updated_at: str


class PublishReviewRequest(BaseModel):
    comments_only: bool = True
    include_general_summary: bool = True
    github_token: str | None = None


class PatchEvalExpectation(BaseModel):
    id: str
    file: str
    target_file: str
    start_line: int
    end_line: int
    category: str
    min_severity: str
    title: str
    description: str


class ReviewEvalMetrics(BaseModel):
    detection_recall: float
    strict_recall: float
    precision: float
    localization_accuracy: float
    false_positives_per_100_lines: float
    total_seeded: int
    matched_seeded: int
    total_findings: int
    latency_ms: float
    cost_usd: float
    patches_evaluated: int

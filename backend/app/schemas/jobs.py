"""
Pydantic v2 schemas for background jobs and SSE events (§6.2 & §12).
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class JobError(BaseModel):
    code: str
    message: str


class JobResponse(BaseModel):
    id: str
    type: str
    repo_id: str
    user_id: str
    status: str
    stage: str
    progress: int
    message: str
    counters: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    error: JobError | None = None
    cancel_requested: bool = False
    created_at: datetime | str
    started_at: datetime | str | None = None
    finished_at: datetime | str | None = None


class JobEvent(BaseModel):
    job_id: str
    repo_id: str
    stage: str
    progress: int
    message: str
    counters: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    status: str

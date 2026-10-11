from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.retrieval import RetrievalStrategy, RouteResult
from app.services.chat.citations import ValidCitation
from app.services.chat.confidence import ConfidenceResult
from app.services.llm.base import LLMUsage


class ConversationCreate(BaseModel):
    title: str | None = Field(default=None, max_length=100)


class ConversationUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=100)


class ConversationResponse(BaseModel):
    id: str
    repo_id: str
    user_id: str
    title: str
    message_count: int = 0
    created_at: datetime
    updated_at: datetime


class ConversationListResponse(BaseModel):
    items: list[ConversationResponse]


class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
    strategy: RetrievalStrategy = "auto"
    regenerate_of: str | None = None


class FeedbackRequest(BaseModel):
    rating: Literal["up", "down"]
    comment: str | None = Field(default=None, max_length=1000)


class FeedbackResponse(BaseModel):
    rating: Literal["up", "down"]
    comment: str | None = None
    at: datetime


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    user_id: str
    role: Literal["user", "assistant"]
    content: str
    status: Literal["complete", "stopped", "error"] = "complete"
    route: RouteResult | None = None
    sources: list[dict[str, Any]] = Field(default_factory=list)
    citations: list[ValidCitation] = Field(default_factory=list)
    confidence: ConfidenceResult | None = None
    usage: LLMUsage | None = None
    latency_ms: dict[str, float] = Field(default_factory=dict)
    trace: dict[str, Any] = Field(default_factory=dict)
    cached: bool = False
    feedback: FeedbackResponse | None = None
    created_at: datetime


class ConversationDetailResponse(BaseModel):
    conversation: ConversationResponse
    messages: list[MessageResponse]


class ExportResponse(BaseModel):
    markdown: str
    filename: str

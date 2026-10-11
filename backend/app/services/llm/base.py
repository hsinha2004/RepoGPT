from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, Literal, Protocol, runtime_checkable

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class LLMUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float | None = None


class LLMDelta(BaseModel):
    text: str = ""
    usage: LLMUsage | None = None
    finish_reason: str | None = None


class LLMResult(BaseModel):
    text: str
    parsed: Any | None = None
    usage: LLMUsage = Field(default_factory=LLMUsage)
    model: str
    finish_reason: str = "stop"
    latency_ms: float = 0.0


@runtime_checkable
class LLMProvider(Protocol):
    name: str

    async def complete(
        self,
        messages: list[ChatMessage],
        *,
        model: str,
        max_tokens: int = 1500,
        temperature: float = 0.1,
        response_schema: type[BaseModel] | None = None,
        timeout: float | None = None,
    ) -> LLMResult: ...

    def stream(
        self,
        messages: list[ChatMessage],
        *,
        model: str,
        max_tokens: int = 1500,
        temperature: float = 0.1,
        timeout: float | None = None,
    ) -> AsyncIterator[LLMDelta]: ...

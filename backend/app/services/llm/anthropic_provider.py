from __future__ import annotations

import time
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

import structlog
from anthropic import APIStatusError, APITimeoutError, AsyncAnthropic, RateLimitError
from pydantic import BaseModel
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter

from app.services.llm.base import ChatMessage, LLMDelta, LLMResult, LLMUsage
from app.services.llm.limiter import LLMLimiter
from app.services.llm.pricing import calculate_cost
from app.services.llm.structured import make_repair_message, parse_structured_response

if TYPE_CHECKING:
    pass

logger = structlog.get_logger(__name__)


class AnthropicProvider:
    """Official Anthropic SDK provider implementation (§9.7)."""

    name: str = "anthropic"

    def __init__(
        self,
        api_key: str,
        limiter: LLMLimiter | None = None,
        pricing_json: str | None = None,
    ) -> None:
        self.client = AsyncAnthropic(api_key=api_key)
        self.limiter = limiter or LLMLimiter(provider="anthropic")
        self.pricing_json = pricing_json

    @retry(
        retry=retry_if_exception_type((RateLimitError, APIStatusError, APITimeoutError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=1.0, max=10.0),
        reraise=True,
    )
    async def complete(
        self,
        messages: list[ChatMessage],
        *,
        model: str,
        max_tokens: int = 1500,
        temperature: float = 0.1,
        response_schema: type[BaseModel] | None = None,
        timeout: float | None = None,
    ) -> LLMResult:
        system_content, user_messages = self._format_messages(messages)

        current_messages = list(user_messages)
        attempts = 0
        last_error = ""

        while attempts < 3:
            attempts += 1
            start_time = time.perf_counter()

            async with self.limiter.acquire():
                kwargs: dict[str, Any] = {
                    "model": model,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "messages": current_messages,
                }
                if system_content:
                    kwargs["system"] = system_content
                if timeout:
                    kwargs["timeout"] = timeout

                response = await self.client.messages.create(**kwargs)

            latency = round((time.perf_counter() - start_time) * 1000, 2)
            content_text = ""
            for block in response.content:
                if block.type == "text":
                    content_text += block.text

            prompt_tokens = response.usage.input_tokens
            completion_tokens = response.usage.output_tokens
            cost = calculate_cost(
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                pricing_override_json=self.pricing_json,
            )
            usage = LLMUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                cost_usd=cost,
            )

            if response_schema is None:
                return LLMResult(
                    text=content_text,
                    parsed=None,
                    usage=usage,
                    model=model,
                    finish_reason=response.stop_reason or "stop",
                    latency_ms=latency,
                )

            # Validate structured output
            parsed, error_msg = parse_structured_response(content_text, response_schema)
            if parsed is not None:
                return LLMResult(
                    text=content_text,
                    parsed=parsed,
                    usage=usage,
                    model=model,
                    finish_reason=response.stop_reason or "stop",
                    latency_ms=latency,
                )

            last_error = error_msg or "Failed to parse schema."
            if attempts < 3:
                # Add repair message and retry
                current_messages.append({"role": "assistant", "content": content_text})
                current_messages.append(
                    {"role": "user", "content": make_repair_message(last_error, response_schema)}
                )

        schema_name = response_schema.__name__ if response_schema else "schema"
        raise ValueError(
            f"Failed to produce structured output matching {schema_name}: {last_error}"
        )

    async def stream(
        self,
        messages: list[ChatMessage],
        *,
        model: str,
        max_tokens: int = 1500,
        temperature: float = 0.1,
        timeout: float | None = None,
    ) -> AsyncIterator[LLMDelta]:
        system_content, user_messages = self._format_messages(messages)

        async with self.limiter.acquire():
            kwargs: dict[str, Any] = {
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": user_messages,
            }
            if system_content:
                kwargs["system"] = system_content
            if timeout:
                kwargs["timeout"] = timeout

            async with self.client.messages.stream(**kwargs) as stream:
                async for text in stream.text_stream:
                    yield LLMDelta(text=text)

                final_msg = await stream.get_final_message()
                prompt_tokens = final_msg.usage.input_tokens
                completion_tokens = final_msg.usage.output_tokens
                cost = calculate_cost(
                    model=model,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    pricing_override_json=self.pricing_json,
                )
                usage = LLMUsage(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=prompt_tokens + completion_tokens,
                    cost_usd=cost,
                )
                yield LLMDelta(text="", usage=usage, finish_reason=final_msg.stop_reason or "stop")

    def _format_messages(self, messages: list[ChatMessage]) -> tuple[str, list[dict[str, str]]]:
        system_parts: list[str] = []
        user_msgs: list[dict[str, str]] = []

        for m in messages:
            if m.role == "system":
                system_parts.append(m.content)
            else:
                user_msgs.append({"role": m.role, "content": m.content})

        return "\n\n".join(system_parts), user_msgs

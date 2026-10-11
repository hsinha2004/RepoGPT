from __future__ import annotations

import time
from collections.abc import AsyncIterator
from typing import Any

import structlog
from openai import APIStatusError, APITimeoutError, AsyncOpenAI, RateLimitError
from pydantic import BaseModel
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter

from app.services.llm.base import ChatMessage, LLMDelta, LLMResult, LLMUsage
from app.services.llm.limiter import LLMLimiter
from app.services.llm.pricing import calculate_cost
from app.services.llm.structured import make_repair_message, parse_structured_response

logger = structlog.get_logger(__name__)


class OpenAICompatibleProvider:
    """Official OpenAI SDK provider supporting all OpenAI-compatible endpoints (§9.7).

    Covers OpenAI, Gemini OpenAI endpoint, Groq, OpenRouter, Ollama, and LM Studio.
    """

    def __init__(
        self,
        name: str = "openai",
        api_key: str | None = None,
        base_url: str | None = None,
        limiter: LLMLimiter | None = None,
        pricing_json: str | None = None,
    ) -> None:
        self.name = name
        # Ollama and local models do not require a real API key
        resolved_key = api_key or "sk-dummy-key"
        self.client = AsyncOpenAI(api_key=resolved_key, base_url=base_url)
        self.limiter = limiter or LLMLimiter(provider=name)
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
        formatted = [{"role": m.role, "content": m.content} for m in messages]
        current_messages = list(formatted)
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
                if response_schema is not None:
                    # Instruct JSON mode where supported
                    try:
                        kwargs["response_format"] = {"type": "json_object"}
                    except Exception:
                        pass
                if timeout:
                    kwargs["timeout"] = timeout

                response = await self.client.chat.completions.create(**kwargs)

            latency = round((time.perf_counter() - start_time) * 1000, 2)
            content_text = ""
            finish_reason = "stop"
            if response.choices:
                choice = response.choices[0]
                content_text = choice.message.content or ""
                finish_reason = choice.finish_reason or "stop"

            prompt_tokens = (
                response.usage.prompt_tokens
                if response.usage
                else sum(len(m["content"].split()) for m in current_messages)
            )
            completion_tokens = (
                response.usage.completion_tokens if response.usage else len(content_text.split())
            )
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
                    finish_reason=finish_reason,
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
                    finish_reason=finish_reason,
                    latency_ms=latency,
                )

            last_error = error_msg or "Failed to validate structured schema."
            if attempts < 3:
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
        formatted = [{"role": m.role, "content": m.content} for m in messages]

        async with self.limiter.acquire():
            kwargs: dict[str, Any] = {
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": formatted,
                "stream": True,
                "stream_options": {"include_usage": True},
            }
            if timeout:
                kwargs["timeout"] = timeout

            stream = await self.client.chat.completions.create(**kwargs)
            collected_text: list[str] = []
            final_usage: LLMUsage | None = None
            finish_reason = "stop"

            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    delta_text = chunk.choices[0].delta.content
                    collected_text.append(delta_text)
                    yield LLMDelta(text=delta_text)
                if chunk.choices and chunk.choices[0].finish_reason:
                    finish_reason = chunk.choices[0].finish_reason

                if getattr(chunk, "usage", None) is not None:
                    u = chunk.usage
                    p_tok = u.prompt_tokens
                    c_tok = u.completion_tokens
                    cost = calculate_cost(
                        model=model,
                        prompt_tokens=p_tok,
                        completion_tokens=c_tok,
                        pricing_override_json=self.pricing_json,
                    )
                    final_usage = LLMUsage(
                        prompt_tokens=p_tok,
                        completion_tokens=c_tok,
                        total_tokens=p_tok + c_tok,
                        cost_usd=cost,
                    )

            if final_usage is None:
                full_text = "".join(collected_text)
                prompt_tokens = sum(len(m.content.split()) for m in messages)
                completion_tokens = len(full_text.split())
                cost = calculate_cost(
                    model=model,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    pricing_override_json=self.pricing_json,
                )
                final_usage = LLMUsage(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=prompt_tokens + completion_tokens,
                    cost_usd=cost,
                )

            yield LLMDelta(text="", usage=final_usage, finish_reason=finish_reason)

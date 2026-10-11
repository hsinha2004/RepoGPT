from __future__ import annotations

import asyncio
import re
import time
from collections.abc import AsyncIterator

from pydantic import BaseModel

from app.services.llm.base import ChatMessage, LLMDelta, LLMResult, LLMUsage
from app.services.retrieval.router.heuristic import route_heuristically


class FakeProvider:
    """Deterministic LLM Provider for offline mode, testing, and CI (§9.7)."""

    name: str = "fake"

    async def complete(
        self,
        messages: list[ChatMessage],
        *,
        model: str = "fake",
        max_tokens: int = 1500,
        temperature: float = 0.1,
        response_schema: type[BaseModel] | None = None,
        timeout: float | None = None,
    ) -> LLMResult:
        _ = (max_tokens, temperature, timeout)
        start_time = time.perf_counter()
        last_message = messages[-1].content if messages else ""

        # 1. Structured output handling
        if response_schema is not None:
            schema_fields = set(getattr(response_schema, "model_fields", {}).keys())

            # RouteResult schema
            if "intent" in schema_fields and "strategy" in schema_fields:
                route = route_heuristically(last_message)
                latency = round((time.perf_counter() - start_time) * 1000, 2)
                return LLMResult(
                    text=route.model_dump_json(),
                    parsed=route,
                    usage=LLMUsage(
                        prompt_tokens=40, completion_tokens=30, total_tokens=70, cost_usd=0.0
                    ),
                    model=model,
                    finish_reason="stop",
                    latency_ms=latency,
                )

            # Grounding check schema
            if "verdict" in schema_fields:
                data = {"verdict": "supported", "unsupported_claims": []}
                parsed = response_schema.model_validate(data)
                latency = round((time.perf_counter() - start_time) * 1000, 2)
                return LLMResult(
                    text=parsed.model_dump_json(),
                    parsed=parsed,
                    usage=LLMUsage(
                        prompt_tokens=50, completion_tokens=15, total_tokens=65, cost_usd=0.0
                    ),
                    model=model,
                    finish_reason="stop",
                    latency_ms=latency,
                )

            # Reformulate schema
            if "search_queries" in schema_fields:
                q_clean = re.sub(r"[^\w\s]", "", last_message).strip()
                data = {
                    "search_queries": [f"{q_clean} definition", f"{q_clean} service"],
                    "hypothetical_snippet": "def execute_task(): pass",
                }
                parsed = response_schema.model_validate(data)
                latency = round((time.perf_counter() - start_time) * 1000, 2)
                return LLMResult(
                    text=parsed.model_dump_json(),
                    parsed=parsed,
                    usage=LLMUsage(
                        prompt_tokens=60, completion_tokens=25, total_tokens=85, cost_usd=0.0
                    ),
                    model=model,
                    finish_reason="stop",
                    latency_ms=latency,
                )

            # Generic schema: attempt default instantiation
            try:
                parsed = response_schema()
                latency = round((time.perf_counter() - start_time) * 1000, 2)
                return LLMResult(
                    text=parsed.model_dump_json(),
                    parsed=parsed,
                    usage=LLMUsage(
                        prompt_tokens=30, completion_tokens=20, total_tokens=50, cost_usd=0.0
                    ),
                    model=model,
                    finish_reason="stop",
                    latency_ms=latency,
                )
            except Exception:
                pass

        # 2. Text generation (Extractive QA Answer with [S#] citations)
        answer_text = self._generate_extractive_answer(messages)
        latency = round((time.perf_counter() - start_time) * 1000, 2)
        prompt_tokens = sum(len(m.content.split()) for m in messages)
        completion_tokens = len(answer_text.split())

        return LLMResult(
            text=answer_text,
            parsed=None,
            usage=LLMUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                cost_usd=0.0,
            ),
            model=model,
            finish_reason="stop",
            latency_ms=latency,
        )

    async def stream(
        self,
        messages: list[ChatMessage],
        *,
        model: str = "fake",
        max_tokens: int = 1500,
        temperature: float = 0.1,
        timeout: float | None = None,
    ) -> AsyncIterator[LLMDelta]:
        result = await self.complete(
            messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=timeout,
        )
        words = result.text.split(" ")

        for i, word in enumerate(words):
            token_str = word if i == len(words) - 1 else word + " "
            yield LLMDelta(text=token_str)
            await asyncio.sleep(0.005)

        # Final delta with usage
        yield LLMDelta(text="", usage=result.usage, finish_reason="stop")

    def _generate_extractive_answer(self, messages: list[ChatMessage]) -> str:
        """Builds an extractive answer citing [S#] sources from messages (§9.7)."""
        all_text = " ".join(m.content for m in messages)

        # Extract sources from <sources> XML block
        source_pattern = re.compile(
            r'<source\s+id="([^"]+)"\s+path="([^"]+)"(?:\s+lines="([^"]+)")?(?:\s+symbol="([^"]+)")?[^>]*>(.*?)</source>',
            re.DOTALL,
        )
        sources = source_pattern.findall(all_text)

        if not sources:
            return (
                "I could not find specific references to this query in the indexed repository code. "
                "Please verify the module or symbol name or check the repository documentation."
            )

        lines: list[str] = [
            f"In this codebase, the requested functionality is implemented across {len(sources)} key component(s):"
        ]

        for s_id, path, line_range, symbol, content in sources:
            # Pick first clean line from content
            content_lines = [
                cl.strip()
                for cl in content.splitlines()
                if cl.strip() and not cl.strip().startswith("<") and not cl.strip().endswith(">")
            ]
            snippet = content_lines[0] if content_lines else "implementation"
            # Strip line numbering if present ("12 | ...")
            if "|" in snippet:
                snippet = snippet.split("|", 1)[1].strip()

            target = f"`{symbol}`" if symbol else f"`{path}`"
            line_str = f" (lines {line_range})" if line_range else ""
            lines.append(f"- {target}{line_str} defines {snippet[:80]} [{s_id}]")

        lines.append(
            "These definitions coordinate the execution and data flow for the requested behavior."
        )
        return "\n\n".join(lines)

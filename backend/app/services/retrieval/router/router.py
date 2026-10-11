from __future__ import annotations

import structlog

from app.core.config import Settings
from app.schemas.retrieval import RetrievalStrategy, RouteResult
from app.services.retrieval.router.heuristic import route_heuristically

logger = structlog.get_logger(__name__)


class QueryRouter:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.mode = settings.ROUTER_MODE.lower().strip()

    async def route(
        self,
        query: str,
        strategy_override: RetrievalStrategy | None = None,
    ) -> RouteResult:
        """Routes a user query into intent, retrieval strategy, weights, and enrichments."""
        # Stage 1: Deterministic heuristic classification
        heuristic_result = route_heuristically(query)

        final_result = heuristic_result

        # Stage 2: LLM refinement if enabled and provider is configured
        if self.mode in ("llm", "hybrid"):
            # Check if an LLM provider is available (not fake and key provided)
            # In M5, if LLM is offline/fake, fallback cleanly to heuristic
            try:
                # LLM router hook (will connect to LLMProvider in M6)
                pass
            except Exception as e:
                logger.warning("llm_router_failed_fallback_to_heuristic", error=str(e))
                final_result = heuristic_result

        # Apply strategy override if user requested a specific strategy
        if strategy_override and strategy_override != "auto":
            final_result.strategy = strategy_override

        return final_result

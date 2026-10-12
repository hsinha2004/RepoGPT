from __future__ import annotations

import structlog

from app.core.config import Settings, get_settings
from app.services.llm.anthropic_provider import AnthropicProvider
from app.services.llm.base import LLMProvider
from app.services.llm.fake import FakeProvider
from app.services.llm.limiter import LLMLimiter
from app.services.llm.openai_compat_provider import OpenAICompatibleProvider
from app.services.llm.presets import PRESETS

logger = structlog.get_logger(__name__)


def get_llm_provider(settings: Settings | None = None) -> LLMProvider:
    """Constructs the configured LLMProvider instance (§9.7).

    Falls back to FakeProvider if provider is 'fake' or if API key is missing.
    """
    cfg = settings or get_settings()
    provider_name = cfg.LLM_PROVIDER.lower()
    preset = PRESETS.get(provider_name, PRESETS["fake"])

    if provider_name == "fake":
        return FakeProvider()

    # If no API key is configured and not local ollama, gracefully fall back to FakeProvider
    if not cfg.LLM_API_KEY and provider_name != "ollama":
        logger.info(
            "llm_provider_offline_mode",
            requested=provider_name,
            reason="No LLM_API_KEY provided; using deterministic FakeProvider for offline operation",
        )
        return FakeProvider()

    limiter = LLMLimiter(
        provider=provider_name,
        max_rpm=cfg.LLM_MAX_RPM,
        max_concurrency=cfg.LLM_MAX_CONCURRENCY,
    )

    if provider_name == "anthropic":
        return AnthropicProvider(
            api_key=cfg.LLM_API_KEY or "",
            limiter=limiter,
            pricing_json=cfg.LLM_PRICING_JSON,
        )

    # All OpenAI-compatible providers (Gemini, OpenAI, Groq, OpenRouter, Ollama)
    base_url = cfg.LLM_BASE_URL or preset.default_base_url
    return OpenAICompatibleProvider(
        name=provider_name,
        api_key=cfg.LLM_API_KEY,
        base_url=base_url,
        limiter=limiter,
        pricing_json=cfg.LLM_PRICING_JSON,
    )


def resolve_model_name(settings: Settings, fast: bool = False) -> str:
    """Resolves primary or fast model name from settings or provider presets (§9.7)."""
    provider_name = settings.LLM_PROVIDER.lower()
    preset = PRESETS.get(provider_name, PRESETS["fake"])

    if fast:
        return settings.LLM_FAST_MODEL or preset.default_fast_model
    return settings.LLM_MODEL or preset.default_model

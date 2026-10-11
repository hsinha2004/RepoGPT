from __future__ import annotations

import json
from typing import Any

# Pricing in USD per 1,000,000 tokens (input, output)
MODEL_PRICING: dict[str, tuple[float, float]] = {
    # Anthropic
    "claude-3-5-sonnet-20241022": (3.00, 15.00),
    "claude-3-5-sonnet-latest": (3.00, 15.00),
    "claude-3-5-haiku-20241022": (0.80, 4.00),
    "claude-3-5-haiku-latest": (0.80, 4.00),
    "claude-3-opus-20240229": (15.00, 75.00),
    # OpenAI
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4-turbo": (10.00, 30.00),
    "o1": (15.00, 60.00),
    "o1-mini": (3.00, 12.00),
    "o3-mini": (1.10, 4.40),
    # Google Gemini
    "gemini-1.5-pro": (3.50, 10.50),
    "gemini-1.5-flash": (0.075, 0.30),
    "gemini-1.5-flash-8b": (0.0375, 0.15),
    "gemini-2.0-flash": (0.10, 0.40),
    "gemini-2.0-flash-exp": (0.0, 0.0),
    # Groq (Llama models)
    "llama-3.3-70b-versatile": (0.59, 0.79),
    "llama-3.1-8b-instant": (0.05, 0.08),
    "mixtral-8x7b-32768": (0.24, 0.24),
    # Local & Fake
    "fake": (0.0, 0.0),
    "ollama": (0.0, 0.0),
}


def calculate_cost(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    pricing_override_json: str | None = None,
) -> float | None:
    """Calculates cost in USD for the given model and token counts (§9.7).

    Returns 0.0 for local/fake models, calculated cost for known models,
    or None if model is unknown.
    """
    model_lower = model.lower()

    if "fake" in model_lower or "ollama" in model_lower or "mock" in model_lower:
        return 0.0

    # 1. Check custom overrides from LLM_PRICING_JSON
    if pricing_override_json:
        try:
            overrides: dict[str, Any] = json.loads(pricing_override_json)
            for key, rates in overrides.items():
                if key.lower() in model_lower or model_lower in key.lower():
                    if (
                        isinstance(rates, (list, tuple))
                        and len(rates) == 2
                        and isinstance(rates[0], (int, float))
                        and isinstance(rates[1], (int, float))
                    ):
                        in_rate, out_rate = float(rates[0]), float(rates[1])
                        cost = (
                            prompt_tokens * in_rate + completion_tokens * out_rate
                        ) / 1_000_000.0
                        return round(cost, 6)
        except Exception:
            pass

    # 2. Check built-in pricing table
    for known_model, (in_rate, out_rate) in MODEL_PRICING.items():
        if known_model == model_lower or known_model in model_lower or model_lower in known_model:
            cost = (prompt_tokens * in_rate + completion_tokens * out_rate) / 1_000_000.0
            return round(cost, 6)

    # Unknown model -> never guessed (§9.7)
    return None

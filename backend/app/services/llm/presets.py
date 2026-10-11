from __future__ import annotations

from typing import NamedTuple


class ProviderPreset(NamedTuple):
    name: str
    default_base_url: str | None
    default_model: str
    default_fast_model: str


PRESETS: dict[str, ProviderPreset] = {
    "gemini": ProviderPreset(
        name="gemini",
        default_base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        default_model="gemini-2.0-flash",
        default_fast_model="gemini-1.5-flash",
    ),
    "anthropic": ProviderPreset(
        name="anthropic",
        default_base_url=None,
        default_model="claude-3-5-sonnet-20241022",
        default_fast_model="claude-3-5-haiku-20241022",
    ),
    "openai": ProviderPreset(
        name="openai",
        default_base_url="https://api.openai.com/v1",
        default_model="gpt-4o",
        default_fast_model="gpt-4o-mini",
    ),
    "groq": ProviderPreset(
        name="groq",
        default_base_url="https://api.groq.com/openai/v1",
        default_model="llama-3.3-70b-versatile",
        default_fast_model="llama-3.1-8b-instant",
    ),
    "openrouter": ProviderPreset(
        name="openrouter",
        default_base_url="https://openrouter.ai/api/v1",
        default_model="anthropic/claude-3.5-sonnet",
        default_fast_model="openai/gpt-4o-mini",
    ),
    "ollama": ProviderPreset(
        name="ollama",
        default_base_url="http://localhost:11434/v1",
        default_model="llama3.2:3b",
        default_fast_model="llama3.2:1b",
    ),
    "fake": ProviderPreset(
        name="fake",
        default_base_url=None,
        default_model="fake",
        default_fast_model="fake",
    ),
}

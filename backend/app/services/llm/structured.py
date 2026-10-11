from __future__ import annotations

import json
import re

from pydantic import BaseModel, ValidationError


def extract_json_from_text(text: str) -> dict | list | None:
    """Extracts first valid JSON object or list from text, stripping code markdown fences."""
    # 1. Direct parse attempt
    clean = text.strip()
    if clean.startswith("```"):
        # Strip markdown fence
        lines = clean.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        clean = "\n".join(lines).strip()

    try:
        return json.loads(clean)
    except Exception:
        pass

    # 2. Regex search for { ... } or [ ... ]
    match = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
    if match:
        snippet = match.group(1).strip()
        try:
            return json.loads(snippet)
        except Exception:
            pass

    return None


def parse_structured_response[T: BaseModel](
    text: str, schema: type[T]
) -> tuple[T | None, str | None]:
    """Attempts to parse structured output according to given schema.

    Returns (parsed_instance, None) on success, or (None, error_description) on failure.
    """
    data = extract_json_from_text(text)
    if data is None:
        return None, "No valid JSON object or array found in output."

    if not isinstance(data, dict):
        return None, f"Expected JSON object, got {type(data).__name__}."

    try:
        instance = schema.model_validate(data)
        return instance, None
    except ValidationError as val_err:
        return None, str(val_err)


def make_repair_message(error_description: str, schema: type[BaseModel]) -> str:
    """Creates a corrective repair instruction message for retry loops (§9.7)."""
    schema_json = json.dumps(schema.model_json_schema(), indent=2)
    return (
        f"Your previous response could not be validated:\n{error_description}\n\n"
        "Please fix the issues and return ONLY a valid JSON object matching this exact schema:\n"
        f"```json\n{schema_json}\n```\n"
        "Do not include any introductory or concluding text."
    )

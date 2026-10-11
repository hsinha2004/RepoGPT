from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel

CITATION_REGEX = re.compile(r"\[S(\d+)\]")


class ValidCitation(BaseModel):
    source_id: str
    path: str
    start_line: int
    end_line: int
    symbol: str | None = None


class CitationVerificationResult(BaseModel):
    valid: list[ValidCitation]
    removed: list[str]
    cleaned_text: str
    total_found: int


def verify_and_clean_citations(
    text: str,
    sources_map: dict[str, dict[str, Any]],
) -> CitationVerificationResult:
    """Extracts [S#] citations from text, validates against sources, and removes invalid ones (§9.5).

    Args:
        text: The generated answer text.
        sources_map: Mapping from source ID (e.g. "S1", "S2") to source metadata dict.
    """
    found_matches = CITATION_REGEX.findall(text)
    total_found = len(found_matches)

    valid_citations: list[ValidCitation] = []
    seen_valid_ids: set[str] = set()
    removed_ids: set[str] = set()

    for num_str in found_matches:
        s_id = f"S{num_str}"
        if s_id in sources_map:
            if s_id not in seen_valid_ids:
                seen_valid_ids.add(s_id)
                meta = sources_map[s_id]
                valid_citations.append(
                    ValidCitation(
                        source_id=s_id,
                        path=meta.get("path", ""),
                        start_line=meta.get("start_line", 1),
                        end_line=meta.get("end_line", 1),
                        symbol=meta.get("symbol_name") or meta.get("symbol"),
                    )
                )
        else:
            removed_ids.add(s_id)

    # Clean invalid citations from text
    def replace_citation(match: re.Match[str]) -> str:
        s_id = f"S{match.group(1)}"
        if s_id in removed_ids:
            return ""
        return match.group(0)

    cleaned_text = CITATION_REGEX.sub(replace_citation, text)
    # Clean up any empty double spaces left by removed citations
    cleaned_text = re.sub(r" +([.,;!?])", r"\1", cleaned_text)

    return CitationVerificationResult(
        valid=valid_citations,
        removed=sorted(removed_ids),
        cleaned_text=cleaned_text,
        total_found=total_found,
    )

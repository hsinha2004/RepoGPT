from __future__ import annotations

import math
import re
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.services.chat.citations import ValidCitation

ConfidenceLabel = Literal["High", "Medium", "Low", "N/A"]


class ConfidenceFactors(BaseModel):
    r: float = Field(ge=0.0, le=1.0, description="Retrieval relevance")
    c: float = Field(ge=0.0, le=1.0, description="Citation validity")
    k: float = Field(ge=0.0, le=1.0, description="Citation coverage")
    g: float | None = Field(default=None, description="Grounding score")


class ConfidenceResult(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    label: ConfidenceLabel
    factors: ConfidenceFactors
    insufficient: bool = False


def _calculate_retrieval_relevance(
    sources_map: dict[str, dict[str, Any]],
    valid_citations: list[ValidCitation],
) -> float:
    """Computes R component: relevance of cited sources (or top 3 if none cited)."""
    target_ids = (
        [c.source_id for c in valid_citations] if valid_citations else list(sources_map.keys())[:3]
    )
    if not target_ids:
        return 0.0

    scores: list[float] = []
    for s_id in target_ids:
        meta = sources_map.get(s_id, {})
        rerank_score = meta.get("rerank_score")
        if rerank_score is not None:
            # Map cross-encoder score via sigmoid
            sig = 1.0 / (1.0 + math.exp(-float(rerank_score)))
            scores.append(max(0.0, min(1.0, sig)))
        else:
            base_score = float(meta.get("score", 0.0))
            # clamp((score - 0.2) / 0.6, 0.0, 1.0)
            norm = (base_score - 0.2) / 0.6 if 0.6 != 0 else base_score
            scores.append(max(0.0, min(1.0, norm)))

    return sum(scores) / len(scores) if scores else 0.0


def _calculate_citation_coverage(text: str, valid_citation_ids: set[str]) -> float:
    """Computes K component: fraction of paragraphs/list items containing >= 1 valid citation."""
    # Strip markdown code blocks
    text_without_code = re.sub(r"```.*?```", "", text, flags=re.DOTALL)

    blocks: list[str] = []
    for line_or_p in text_without_code.split("\n\n"):
        clean_p = line_or_p.strip()
        if not clean_p or clean_p.startswith("#"):
            continue
        # Split individual list items if present
        sub_items = [
            item.strip()
            for item in clean_p.splitlines()
            if item.strip() and not item.strip().startswith("#")
        ]
        blocks.extend(sub_items)

    if not blocks:
        return 0.0

    cited_blocks = 0
    for block in blocks:
        found = re.findall(r"\[S(\d+)\]", block)
        if any(f"S{num}" in valid_citation_ids for num in found):
            cited_blocks += 1

    return cited_blocks / len(blocks)


def compute_confidence(
    text: str,
    sources_map: dict[str, dict[str, Any]],
    valid_citations: list[ValidCitation],
    total_citations_found: int,
    intent: str,
    grounding_verdict: str | None = None,
    insufficient: bool = False,
) -> ConfidenceResult:
    """Computes overall confidence score according to §9.6.

    confidence = 0.35*R + 0.20*C + 0.15*K + 0.30*G (or renormalised without G).
    Capped at 0.35 if insufficient=True.
    """
    if intent in ("general", "out_of_scope"):
        return ConfidenceResult(
            score=0.0,
            label="N/A",
            factors=ConfidenceFactors(r=0.0, c=0.0, k=0.0, g=None),
            insufficient=insufficient,
        )

    # 1. R: Retrieval relevance
    r = _calculate_retrieval_relevance(sources_map, valid_citations)

    # 2. C: Citation validity
    if total_citations_found > 0:
        c = len(valid_citations) / total_citations_found
    else:
        c = 0.0

    # 3. K: Citation coverage
    valid_ids = {cit.source_id for cit in valid_citations}
    k = _calculate_citation_coverage(text, valid_ids)

    # 4. G: Grounding score
    g: float | None = None
    if grounding_verdict is not None:
        v_lower = grounding_verdict.lower()
        if v_lower == "supported":
            g = 1.0
        elif v_lower == "partial":
            g = 0.5
        else:
            g = 0.0

    # Calculate weighted score
    if g is not None:
        raw_score = 0.35 * r + 0.20 * c + 0.15 * k + 0.30 * g
    else:
        # Renormalise weights: 0.35/0.7, 0.20/0.7, 0.15/0.7
        raw_score = (0.35 / 0.70) * r + (0.20 / 0.70) * c + (0.15 / 0.70) * k

    final_score = min(raw_score, 0.35) if insufficient else raw_score
    final_score = max(0.0, min(1.0, round(final_score, 4)))

    # Determine label
    if final_score >= 0.75:
        label: ConfidenceLabel = "High"
    elif final_score >= 0.50:
        label = "Medium"
    else:
        label = "Low"

    return ConfidenceResult(
        score=final_score,
        label=label,
        factors=ConfidenceFactors(
            r=round(r, 4),
            c=round(c, 4),
            k=round(k, 4),
            g=round(g, 4) if g is not None else None,
        ),
        insufficient=insufficient,
    )

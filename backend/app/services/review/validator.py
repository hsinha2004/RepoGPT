"""
Review finding validation, deduplication, and risk scoring engine (§10.2, §10.3).
"""

from __future__ import annotations

import uuid
from typing import Any

SEVERITY_WEIGHTS = {
    "critical": 5,
    "high": 4,
    "medium": 3,
    "low": 2,
    "info": 1,
}

VALID_CATEGORIES = {
    "bug",
    "security",
    "performance",
    "error_handling",
    "concurrency",
    "api_contract",
    "testing",
    "maintainability",
    "documentation",
}


class ReviewValidator:
    """
    Validates, filters, dedupes, and ranks code review findings (§10.2).
    """

    def __init__(self, min_confidence: float = 0.65, max_findings: int = 30) -> None:
        self.min_confidence = min_confidence
        self.max_findings = max_findings

    def validate_and_rank(
        self,
        raw_findings: list[dict[str, Any]],
        file_changed_lines: dict[str, set[int]],
        valid_evidence_ids: set[str] | None = None,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str, dict[str, int]]:
        """
        Validates findings against changed hunk lines and ranks them.
        Returns:
            (validated_findings, general_comments, risk_level, stats)
        """
        valid_evidence = valid_evidence_ids or set()
        validated: list[dict[str, Any]] = []
        general_comments: list[dict[str, Any]] = []

        for item in raw_findings:
            path = item.get("path", "")
            start_line = int(item.get("start_line", 1))
            end_line = int(item.get("end_line", start_line))
            confidence = float(item.get("confidence", 0.8))

            # Filter below confidence threshold
            if confidence < self.min_confidence:
                continue

            # Check if line anchors inside a changed hunk
            allowed_lines = file_changed_lines.get(path, set())
            is_anchored = any(ln in allowed_lines for ln in range(start_line, end_line + 1))

            category = item.get("category", "bug").lower()
            if category not in VALID_CATEGORIES:
                category = "bug"

            severity = item.get("severity", "medium").lower()
            if severity not in SEVERITY_WEIGHTS:
                severity = "medium"

            title = str(item.get("title", ""))[:80]
            if not title:
                title = f"Potential {category} issue"

            # Filter evidence references
            filtered_evidence = []
            for ev in item.get("evidence", []):
                sid = ev.get("source_id", "")
                if not valid_evidence or sid in valid_evidence:
                    filtered_evidence.append(ev)

            normalized_finding = {
                "id": item.get("id") or str(uuid.uuid4())[:8],
                "path": path,
                "start_line": start_line,
                "end_line": end_line,
                "side": "RIGHT",
                "category": category,
                "severity": severity,
                "title": title,
                "explanation": item.get("explanation", ""),
                "suggestion": item.get("suggestion"),
                "suggested_code": item.get("suggested_code"),
                "evidence": filtered_evidence,
                "confidence": round(confidence, 2),
                "origin": item.get("origin", "llm"),
                "status": "pending",
                "user_note": None,
            }

            if is_anchored:
                validated.append(normalized_finding)
            else:
                general_comments.append(
                    {
                        "path": path,
                        "title": title,
                        "comment": item.get("explanation", ""),
                        "category": category,
                    }
                )

        # Deduplicate near-duplicates (same file, overlapping lines, similar title)
        deduped: list[dict[str, Any]] = []
        for f in validated:
            is_duplicate = False
            for d in deduped:
                if d["path"] == f["path"]:
                    # Line overlap
                    lines_overlap = not (
                        f["end_line"] < d["start_line"] or f["start_line"] > d["end_line"]
                    )
                    if lines_overlap and (
                        f["category"] == d["category"] or f["title"].lower() == d["title"].lower()
                    ):
                        is_duplicate = True
                        break
            if not is_duplicate:
                deduped.append(f)

        # Sort by (severity_weight * confidence) descending
        deduped.sort(
            key=lambda x: SEVERITY_WEIGHTS.get(x["severity"], 1) * x["confidence"],
            reverse=True,
        )

        # Cap at max_findings
        final_findings = deduped[: self.max_findings]

        # Calculate risk level
        risk_level = "low"
        severities = [f["severity"] for f in final_findings]
        if "critical" in severities:
            risk_level = "critical"
        elif "high" in severities or severities.count("medium") >= 4:
            risk_level = "high"
        elif "medium" in severities:
            risk_level = "medium"

        stats = {
            "findings_count": len(final_findings),
            "critical_count": severities.count("critical"),
            "high_count": severities.count("high"),
            "medium_count": severities.count("medium"),
            "low_count": severities.count("low"),
            "info_count": severities.count("info"),
        }

        return final_findings, general_comments, risk_level, stats

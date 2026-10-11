"""
Secret Redaction Service (§8.3).
Scans files before chunking, embedding, storage or display.
Replaces detected secrets with <REDACTED_SECRET:{detector}> preserving line count.
"""

from dataclasses import dataclass, field

from app.services.redaction.detectors import (
    MatchSpan,
    find_generic_secrets,
    find_known_secrets,
)


@dataclass
class RedactionResult:
    redacted_text: str
    redaction_count: int
    detector_counts: dict[str, int] = field(default_factory=dict)


class SecretRedactor:
    """Scans and redacts credentials from source text."""

    def redact(self, text: str) -> RedactionResult:
        if not text:
            return RedactionResult(redacted_text="", redaction_count=0)

        known_spans = find_known_secrets(text)
        generic_spans = find_generic_secrets(text)

        all_spans = known_spans + generic_spans
        if not all_spans:
            return RedactionResult(
                redacted_text=text,
                redaction_count=0,
                detector_counts={},
            )

        # Sort spans by start asc, end desc (longer first)
        all_spans.sort(key=lambda s: (s.start, -(s.end - s.start)))

        # Deduplicate overlapping spans
        non_overlapping: list[MatchSpan] = []
        last_end = -1
        for span in all_spans:
            if span.start >= last_end:
                non_overlapping.append(span)
                last_end = span.end

        detector_counts: dict[str, int] = {}
        for span in non_overlapping:
            detector_counts[span.detector] = detector_counts.get(span.detector, 0) + 1

        # Replace in reverse order so offsets remain valid
        non_overlapping.sort(key=lambda s: s.start, reverse=True)
        result_chars = list(text)

        for span in non_overlapping:
            replacement = (
                span.replacement
                if span.replacement is not None
                else f"<REDACTED_SECRET:{span.detector}>"
            )
            result_chars[span.start : span.end] = list(replacement)

        redacted_text = "".join(result_chars)

        return RedactionResult(
            redacted_text=redacted_text,
            redaction_count=len(non_overlapping),
            detector_counts=detector_counts,
        )

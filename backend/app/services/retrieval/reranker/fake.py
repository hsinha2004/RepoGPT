from __future__ import annotations

import re


class FakeRerankerProvider:
    name: str = "fake"
    model_name: str = "fake-cross-encoder-v1"

    async def rerank(self, query: str, texts: list[str]) -> list[float]:
        if not texts:
            return []

        query_terms = set(re.findall(r"\w+", query.lower()))
        scores: list[float] = []

        for text in texts:
            if not query_terms:
                scores.append(0.1)
                continue

            text_lower = text.lower()
            text_terms = set(re.findall(r"\w+", text_lower))

            # Term overlap (Jaccard-like recall)
            matched = query_terms.intersection(text_terms)
            overlap_score = len(matched) / max(len(query_terms), 1)

            # Substring bonus for full query phrase or identifier presence
            bonus = 0.0
            if query.lower().strip() in text_lower:
                bonus += 0.3
            for term in query_terms:
                if len(term) >= 4 and term in text_lower:
                    bonus += 0.05

            final_score = min(1.0, round(0.1 + (overlap_score * 0.6) + bonus, 4))
            scores.append(final_score)

        return scores

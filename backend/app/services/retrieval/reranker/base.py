from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class RerankerProvider(Protocol):
    name: str
    model_name: str

    async def rerank(self, query: str, texts: list[str]) -> list[float]:
        """Compute cross-encoder relevance scores for (query, text) pairs.

        Returns a list of float scores with the same length as `texts`.
        Higher score indicates higher relevance.
        """
        ...

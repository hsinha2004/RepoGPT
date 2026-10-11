from __future__ import annotations

import math

import anyio
import structlog
from fastembed.rerank.cross_encoder import TextCrossEncoder

logger = structlog.get_logger(__name__)


class FastEmbedRerankerProvider:
    name: str = "fastembed"

    def __init__(self, model_name: str, cache_dir: str | None = None) -> None:
        self.model_name = model_name
        self.cache_dir = cache_dir
        self._model: TextCrossEncoder | None = None

    def _get_model(self) -> TextCrossEncoder:
        if self._model is None:
            logger.info("loading_reranker_model", model=self.model_name, cache_dir=self.cache_dir)
            self._model = TextCrossEncoder(
                model_name=self.model_name,
                cache_dir=self.cache_dir,
            )
        return self._model

    def _sync_rerank(self, query: str, texts: list[str]) -> list[float]:
        if not texts:
            return []
        model = self._get_model()
        raw_scores: list[float] = list(model.rerank(query=query, documents=texts))

        # Convert logits to probability via sigmoid for normalized 0..1 scale
        normalized: list[float] = []
        for s in raw_scores:
            try:
                # Clamp to avoid overflow
                clamped = max(-20.0, min(20.0, float(s)))
                prob = 1.0 / (1.0 + math.exp(-clamped))
                normalized.append(round(prob, 4))
            except Exception:
                normalized.append(0.0)
        return normalized

    async def rerank(self, query: str, texts: list[str]) -> list[float]:
        if not texts:
            return []
        return await anyio.to_thread.run_sync(self._sync_rerank, query, texts)

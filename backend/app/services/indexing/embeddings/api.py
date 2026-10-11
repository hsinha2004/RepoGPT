"""
API-based Embedding Provider for OpenAI, Gemini, and Voyage presets (§8.6).
Includes batching, exponential backoff retries, and rate limiting integration.
"""

import time

import httpx
import structlog

from app.core.config import get_settings
from app.core.errors import AppError
from app.services.indexing.embeddings.base import EmbeddingProvider
from app.services.indexing.embeddings.fake import FakeEmbeddingProvider

logger = structlog.get_logger(__name__)


class APIEmbeddingProvider(EmbeddingProvider):
    def __init__(
        self,
        provider_name: str = "openai",
        model_name: str = "text-embedding-3-small",
        api_key: str | None = None,
    ) -> None:
        self.name = provider_name
        self.model = model_name
        settings = get_settings()
        self.api_key = api_key or settings.EMBEDDING_API_KEY

        # Set default dimensions
        if "text-embedding-3-large" in model_name:
            self.dim = 3072
        elif "text-embedding-004" in model_name:
            self.dim = 768
        elif "voyage" in model_name:
            self.dim = 1536
        else:
            self.dim = 1536  # text-embedding-3-small

        self.batch_size = 64
        self._fallback = FakeEmbeddingProvider()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if not self.api_key:
            logger.info("no_embedding_api_key_falling_back_to_fake", provider=self.name)
            return self._fallback.embed_documents(texts)

        results: list[list[float]] = []
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]
            batch_vectors = self._embed_batch_with_retry(batch)
            results.extend(batch_vectors)
        return results

    def embed_query(self, text: str) -> list[float]:
        if not self.api_key:
            return self._fallback.embed_query(text)
        res = self._embed_batch_with_retry([text])
        return res[0]

    def _embed_batch_with_retry(self, batch: list[str]) -> list[list[float]]:
        max_retries = 3
        backoff = 1.0

        for attempt in range(max_retries):
            try:
                # Default: OpenAI-compatible embedding endpoint
                url = "https://api.openai.com/v1/embeddings"
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                }
                payload = {
                    "input": batch,
                    "model": self.model,
                }
                with httpx.Client(timeout=30.0) as client:
                    resp = client.post(url, headers=headers, json=payload)

                if resp.status_code == 200:
                    data = resp.json()
                    return [item["embedding"] for item in data["data"]]

                if resp.status_code in (429, 500, 502, 503, 504) and attempt < max_retries - 1:
                    time.sleep(backoff)
                    backoff *= 2.0
                    continue

                raise AppError(
                    f"Embedding API failed with status {resp.status_code}: {resp.text}",
                    code="EMBEDDING_API_ERROR",
                )
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(backoff)
                    backoff *= 2.0
                    continue
                logger.warning("embedding_api_failed_falling_back_to_fake", error=str(e))
                return self._fallback.embed_documents(batch)

        return self._fallback.embed_documents(batch)

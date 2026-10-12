"""
Deterministic Fake Embedding Provider for offline mode and tests (§8.6).
Generates deterministic 256-dimensional L2-normalized bag-of-tokens vectors.
"""

import hashlib
import math
import re

from app.services.indexing.embeddings.base import EmbeddingProvider


class FakeEmbeddingProvider(EmbeddingProvider):
    name = "fake"
    model = "fake-256d"
    dim = 256
    batch_size = 128

    def _embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        if not text:
            vec[0] = 1.0
            return vec

        # Tokenize simply on word characters
        tokens = re.findall(r"\w+", text.lower())
        if not tokens:
            vec[0] = 1.0
            return vec

        for t in tokens:
            h = int(hashlib.md5(t.encode("utf-8"), usedforsecurity=False).hexdigest(), 16)
            idx = h % self.dim
            vec[idx] += 1.0

        # L2-normalize
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0.0:
            return [v / norm for v in vec]
        vec[0] = 1.0
        return vec

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

"""
FastEmbed embedding provider using ONNX runtime and BAAI/bge-small-en-v1.5 (§8.6).
"""

from fastembed import TextEmbedding

from app.core.config import get_settings
from app.services.indexing.embeddings.base import EmbeddingProvider


class FastEmbedProvider(EmbeddingProvider):
    name = "fastembed"
    model = "BAAI/bge-small-en-v1.5"
    dim = 384
    batch_size = 64

    def __init__(self, model_name: str | None = None) -> None:
        if model_name:
            self.model = model_name
        settings = get_settings()
        self._model = TextEmbedding(
            model_name=self.model,
            cache_dir=settings.MODEL_CACHE_DIR,
        )

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors: list[list[float]] = []
        # fastembed.embed generates numpy arrays
        for v in self._model.embed(texts, batch_size=self.batch_size):
            vectors.append(v.tolist())
        return vectors

    def embed_query(self, text: str) -> list[float]:
        # fastembed.query_embed produces query-optimized vector
        if hasattr(self._model, "query_embed"):
            generator = self._model.query_embed(text)
        else:
            generator = self._model.embed([text])
        return next(iter(generator)).tolist()

"""
Base interface for Embedding Providers (§8.6).
"""

from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    name: str
    model: str
    dim: int
    batch_size: int = 64

    @abstractmethod
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embeds a batch of document texts into normalized vectors."""
        pass

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """Embeds a single query string into a normalized vector."""
        pass

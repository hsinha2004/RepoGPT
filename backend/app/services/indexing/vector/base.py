"""
Base VectorStore interface (§6.3).
Unified abstraction across Chroma and FAISS stores.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class VectorMatch:
    id: str
    score: float  # Similarity score (higher is more similar)
    metadata: dict[str, Any]


class VectorStore(ABC):
    def __init__(self, repo_id: str, model_slug: str) -> None:
        self.repo_id = repo_id
        self.model_slug = model_slug

    @abstractmethod
    def upsert(
        self,
        ids: list[str],
        vectors: list[list[float]],
        metadatas: list[dict[str, Any]],
    ) -> None:
        """Inserts or updates vectors with metadata in the store."""
        pass

    @abstractmethod
    def delete(self, ids: list[str]) -> None:
        """Deletes vectors by ID from the store."""
        pass

    @abstractmethod
    def query(
        self,
        vector: list[float],
        k: int = 10,
        where: dict[str, Any] | None = None,
    ) -> list[VectorMatch]:
        """Queries for top k most similar vectors."""
        pass

    @abstractmethod
    def count(self) -> int:
        """Returns the total number of vectors in the collection."""
        pass

    @abstractmethod
    def drop(self) -> None:
        """Drops the vector collection and purges stored files."""
        pass

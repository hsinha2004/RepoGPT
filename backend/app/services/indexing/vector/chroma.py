"""
Chroma VectorStore implementation (§6.3).
Collection per repo and embedding model: rg_{repo_id}_{model_slug} (cosine distance).
"""

import re
from typing import Any

import chromadb
import structlog
from chromadb.api import ClientAPI

from app.core.config import get_settings
from app.services.indexing.vector.base import VectorMatch, VectorStore

logger = structlog.get_logger(__name__)


def clean_slug(s: str) -> str:
    """Creates a Chroma-compliant identifier [a-zA-Z0-9_-]{3,63}."""
    cleaned = re.sub(r"[^a-zA-Z0-9_\-]", "_", s)
    return cleaned[:45]


class ChromaVectorStore(VectorStore):
    def __init__(
        self,
        repo_id: str,
        model_slug: str,
        client: ClientAPI | None = None,
    ) -> None:
        super().__init__(repo_id, model_slug)
        settings = get_settings()

        if client is not None:
            self._client = client
        else:
            try:
                self._client = chromadb.HttpClient(
                    host=settings.CHROMA_HOST,
                    port=settings.CHROMA_PORT,
                )
                self._client.heartbeat()
            except Exception:
                # Fallback to local in-memory or persistent client for tests / offline mode
                import os

                chroma_path = os.path.join(settings.DATA_DIR, "chroma")
                os.makedirs(chroma_path, exist_ok=True)
                self._client = chromadb.PersistentClient(path=chroma_path)

        c_slug = clean_slug(model_slug)
        self.collection_name = f"rg_{repo_id}_{c_slug}"[:63]
        self._col = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def upsert(
        self,
        ids: list[str],
        vectors: list[list[float]],
        metadatas: list[dict[str, Any]],
    ) -> None:
        if not ids:
            return
        # Ensure metadata values are primitives (strings, ints, floats, bools)
        clean_metas = []
        for m in metadatas:
            cm = {}
            for k, v in m.items():
                if v is None:
                    continue
                if isinstance(v, (str, int, float, bool)):
                    cm[k] = v
                else:
                    cm[k] = str(v)
            clean_metas.append(cm)

        self._col.upsert(
            ids=ids,
            embeddings=vectors,  # type: ignore[arg-type]
            metadatas=clean_metas,  # type: ignore[arg-type]
        )

    def delete(self, ids: list[str]) -> None:
        if not ids:
            return
        try:
            self._col.delete(ids=ids)
        except Exception:
            pass

    def query(
        self,
        vector: list[float],
        k: int = 10,
        where: dict[str, Any] | None = None,
    ) -> list[VectorMatch]:
        n_results = min(k, max(1, self.count()))
        if self.count() == 0:
            return []

        res = self._col.query(
            query_embeddings=[vector],  # type: ignore[arg-type]
            n_results=n_results,
            where=where,
            include=["metadatas", "distances"],
        )

        matches: list[VectorMatch] = []
        if res and res["ids"] and len(res["ids"][0]) > 0:
            ids = res["ids"][0]
            metadatas = res["metadatas"][0] if res["metadatas"] else [{}] * len(ids)
            distances = res["distances"][0] if res["distances"] else [0.0] * len(ids)

            for cid, meta, dist in zip(ids, metadatas, distances, strict=False):
                # Convert cosine distance to cosine similarity: sim = 1.0 - dist
                score = 1.0 - float(dist)
                matches.append(
                    VectorMatch(id=cid, score=score, metadata=dict(meta) if meta else {})
                )

        return matches

    def count(self) -> int:
        try:
            return self._col.count()
        except Exception:
            return 0

    def drop(self) -> None:
        try:
            self._client.delete_collection(self.collection_name)
        except Exception:
            pass
        try:
            self._col = self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        except Exception:
            pass

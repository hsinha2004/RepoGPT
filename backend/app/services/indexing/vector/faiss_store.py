"""
FAISS VectorStore implementation (§6.3).
IndexFlatIP on L2-normalized vectors saved at $DATA_DIR/indexes/{repo_id}/{model_slug}/faiss.index.
"""

import json
import os
import re
import shutil
from typing import Any

import faiss
import numpy as np

from app.core.config import get_settings
from app.services.indexing.vector.base import VectorMatch, VectorStore


def clean_slug(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_\-]", "_", s)[:45]


class FAISSVectorStore(VectorStore):
    def __init__(self, repo_id: str, model_slug: str, dim: int = 256) -> None:
        super().__init__(repo_id, model_slug)
        self.dim = dim
        settings = get_settings()
        c_slug = clean_slug(model_slug)
        self.dir_path = os.path.join(settings.DATA_DIR, "indexes", repo_id, c_slug)
        self.index_path = os.path.join(self.dir_path, "faiss.index")
        self.id_map_path = os.path.join(self.dir_path, "id_map.json")

        self._id_map: list[dict[str, Any]] = []  # list of {"id": cid, "metadata": meta}
        self._vectors: list[list[float]] = []
        self._index: faiss.IndexFlatIP | None = None

        self._load()

    def _load(self) -> None:
        if os.path.exists(self.index_path) and os.path.exists(self.id_map_path):
            try:
                self._index = faiss.read_index(self.index_path)  # type: ignore[assignment]
                with open(self.id_map_path, encoding="utf-8") as f:
                    data = json.load(f)
                    self._id_map = data.get("id_map", [])
                    self._vectors = data.get("vectors", [])
                if self._index:
                    self.dim = self._index.d
                return
            except Exception:
                pass

        self._index = faiss.IndexFlatIP(self.dim)
        self._id_map = []
        self._vectors = []

    def _save(self) -> None:
        os.makedirs(self.dir_path, exist_ok=True)
        if self._index:
            faiss.write_index(self._index, self.index_path)
        with open(self.id_map_path, "w", encoding="utf-8") as f:
            json.dump({"id_map": self._id_map, "vectors": self._vectors}, f)

    def upsert(
        self,
        ids: list[str],
        vectors: list[list[float]],
        metadatas: list[dict[str, Any]],
    ) -> None:
        if not ids:
            return

        # Check dimension from first vector
        if vectors:
            self.dim = len(vectors[0])

        # Delete any existing IDs first
        id_set = set(ids)
        keep_indices = [i for i, item in enumerate(self._id_map) if item["id"] not in id_set]

        new_id_map = [self._id_map[i] for i in keep_indices]
        new_vectors = [self._vectors[i] for i in keep_indices]

        # Add new items
        for cid, vec, meta in zip(ids, vectors, metadatas, strict=False):
            new_id_map.append({"id": cid, "metadata": meta})
            new_vectors.append(vec)

        self._id_map = new_id_map
        self._vectors = new_vectors

        # Rebuild index
        self._index = faiss.IndexFlatIP(self.dim)
        if self._vectors:
            np_vecs = np.array(self._vectors, dtype=np.float32)
            faiss.normalize_L2(np_vecs)
            self._index.add(np_vecs)

        self._save()

    def delete(self, ids: list[str]) -> None:
        if not ids or not self._id_map:
            return
        id_set = set(ids)
        keep_indices = [i for i, item in enumerate(self._id_map) if item["id"] not in id_set]

        self._id_map = [self._id_map[i] for i in keep_indices]
        self._vectors = [self._vectors[i] for i in keep_indices]

        self._index = faiss.IndexFlatIP(self.dim)
        if self._vectors:
            np_vecs = np.array(self._vectors, dtype=np.float32)
            faiss.normalize_L2(np_vecs)
            self._index.add(np_vecs)

        self._save()

    def query(
        self,
        vector: list[float],
        k: int = 10,
        where: dict[str, Any] | None = None,
    ) -> list[VectorMatch]:
        if not self._index or self.count() == 0:
            return []

        q_vec = np.array([vector], dtype=np.float32)
        faiss.normalize_L2(q_vec)

        search_k = min(len(self._id_map), max(k * 3, 20))
        distances, indices = self._index.search(q_vec, search_k)

        matches: list[VectorMatch] = []
        for dist, idx in zip(distances[0], indices[0], strict=False):
            if idx < 0 or idx >= len(self._id_map):
                continue
            item = self._id_map[idx]
            meta = item.get("metadata", {})

            # Filter with where dict if provided
            if where:
                matched = True
                for wk, wv in where.items():
                    if meta.get(wk) != wv:
                        matched = False
                        break
                if not matched:
                    continue

            matches.append(VectorMatch(id=item["id"], score=float(dist), metadata=meta))
            if len(matches) >= k:
                break

        return matches

    def count(self) -> int:
        return len(self._id_map)

    def drop(self) -> None:
        if os.path.exists(self.dir_path):
            shutil.rmtree(self.dir_path, ignore_errors=True)
        self._id_map = []
        self._vectors = []
        self._index = faiss.IndexFlatIP(self.dim)

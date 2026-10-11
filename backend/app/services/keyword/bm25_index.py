"""
BM25 Index implementation using bm25s (§8.7).
"""

import json
import logging
import shutil
import threading
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import bm25s  # type: ignore[import-untyped]

from app.core.config import get_settings
from app.services.keyword.tokenizer import tokenize_code

logger = logging.getLogger(__name__)


@dataclass
class BM25Match:
    chunk_id: str
    score: float
    rank: int  # 1-based rank


class BM25Index:
    """Encapsulates a loaded bm25s index and its chunk ID mapping."""

    def __init__(self, retriever: bm25s.BM25, chunk_ids: list[str]) -> None:
        self.retriever = retriever
        self.chunk_ids = chunk_ids

    @classmethod
    def build(cls, chunks: list[dict[str, Any]], index_dir: Path | str) -> "BM25Index":
        """
        Builds a new BM25 index from chunk embed_texts and persists it to index_dir.
        """
        index_path = Path(index_dir)
        index_path.mkdir(parents=True, exist_ok=True)

        chunk_ids: list[str] = []
        corpus_tokens: list[list[str]] = []

        for chunk in chunks:
            c_id = str(chunk.get("id") or chunk.get("_id") or chunk.get("chunk_id") or "")
            text = str(chunk.get("embed_text") or chunk.get("text") or "")
            file_path = chunk.get("file_path")
            tokens = tokenize_code(text, file_path=file_path)
            chunk_ids.append(c_id)
            corpus_tokens.append(tokens)

        retriever = bm25s.BM25()
        if corpus_tokens:
            retriever.index(corpus_tokens)

        # Persist index and chunk IDs
        retriever.save(str(index_path))
        with open(index_path / "chunk_ids.json", "w", encoding="utf-8") as f:
            json.dump(chunk_ids, f)

        logger.info(
            "Built and saved BM25 index with %d chunks to %s",
            len(chunk_ids),
            index_path,
        )
        return cls(retriever=retriever, chunk_ids=chunk_ids)

    @classmethod
    def load(cls, index_dir: Path | str) -> "BM25Index":
        """
        Loads an existing BM25 index and chunk ID map from index_dir.
        """
        index_path = Path(index_dir)
        chunk_ids_file = index_path / "chunk_ids.json"
        if not chunk_ids_file.exists():
            raise FileNotFoundError(f"Missing chunk_ids.json in {index_path}")

        with open(chunk_ids_file, encoding="utf-8") as f:
            chunk_ids = json.load(f)

        retriever = bm25s.BM25.load(str(index_path), load_corpus=False)
        return cls(retriever=retriever, chunk_ids=chunk_ids)

    def search(self, query: str, k: int = 50) -> list[BM25Match]:
        """
        Searches the BM25 index and returns top-k BM25Match results.
        """
        if not self.chunk_ids:
            return []

        query_tokens = tokenize_code(query)
        if not query_tokens:
            return []

        actual_k = min(k, len(self.chunk_ids))
        if actual_k <= 0:
            return []

        # bm25s expects list of queries: [query_tokens]
        doc_indices, scores = self.retriever.retrieve([query_tokens], k=actual_k)

        matches: list[BM25Match] = []
        for idx, score in zip(doc_indices[0], scores[0], strict=False):
            doc_idx = int(idx)
            score_val = float(score)
            if score_val > 0.0 and 0 <= doc_idx < len(self.chunk_ids):
                matches.append(
                    BM25Match(
                        chunk_id=self.chunk_ids[doc_idx],
                        score=score_val,
                        rank=len(matches) + 1,
                    )
                )

        return matches


class BM25IndexManager:
    """
    Thread-safe LRU manager for BM25 indexes in memory (§8.7).
    """

    def __init__(self, maxsize: int = 10) -> None:
        self.maxsize = maxsize
        self._cache: OrderedDict[str, BM25Index] = OrderedDict()
        self._lock = threading.Lock()

    def _get_key(self, repo_id: str, commit_sha: str) -> str:
        return f"{repo_id}:{commit_sha}"

    def get_index_dir(self, repo_id: str, commit_sha: str) -> Path:
        return Path(get_settings().DATA_DIR) / "indexes" / repo_id / commit_sha / "bm25"

    def get_index(self, repo_id: str, commit_sha: str) -> BM25Index | None:
        key = self._get_key(repo_id, commit_sha)
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                return self._cache[key]

        # Not in cache, try loading from disk
        index_dir = self.get_index_dir(repo_id, commit_sha)
        if (index_dir / "chunk_ids.json").exists():
            try:
                index = BM25Index.load(index_dir)
                with self._lock:
                    self._cache[key] = index
                    self._cache.move_to_end(key)
                    if len(self._cache) > self.maxsize:
                        self._cache.popitem(last=False)
                return index
            except Exception as e:
                logger.error("Failed to load BM25 index from %s: %s", index_dir, e)
                return None

        return None

    def put_index(self, repo_id: str, commit_sha: str, index: BM25Index) -> None:
        key = self._get_key(repo_id, commit_sha)
        with self._lock:
            self._cache[key] = index
            self._cache.move_to_end(key)
            if len(self._cache) > self.maxsize:
                self._cache.popitem(last=False)

    def evict(self, repo_id: str, commit_sha: str | None = None) -> None:
        with self._lock:
            if commit_sha is not None:
                key = self._get_key(repo_id, commit_sha)
                self._cache.pop(key, None)
            else:
                prefix = f"{repo_id}:"
                keys_to_remove = [k for k in self._cache if k.startswith(prefix)]
                for k in keys_to_remove:
                    self._cache.pop(k, None)

    def delete_index(self, repo_id: str, commit_sha: str | None = None) -> None:
        self.evict(repo_id, commit_sha)
        if commit_sha is not None:
            dir_to_remove = self.get_index_dir(repo_id, commit_sha)
            if dir_to_remove.exists():
                shutil.rmtree(dir_to_remove, ignore_errors=True)
        else:
            repo_indexes = Path(get_settings().DATA_DIR) / "indexes" / repo_id
            if repo_indexes.exists():
                shutil.rmtree(repo_indexes, ignore_errors=True)


# Process-wide singleton instance
_bm25_manager: BM25IndexManager | None = None
_manager_lock = threading.Lock()


def get_bm25_manager() -> BM25IndexManager:
    global _bm25_manager
    if _bm25_manager is None:
        with _manager_lock:
            if _bm25_manager is None:
                _bm25_manager = BM25IndexManager(maxsize=get_settings().BM25_LRU_CACHE_SIZE)
    return _bm25_manager

"""
Embedding Cache for incremental indexing and query latency (§8.6).
Avoids re-embedding unchanged chunks across commits (keyed by content_hash + model).
Caches query embeddings in Redis with 1-hour TTL.
"""

import hashlib
import json
from typing import Any

from pymongo import UpdateOne

from app.db.mongo import get_collection
from app.db.redis import get_redis_client


class EmbeddingCache:
    def __init__(self, collection: Any | None = None) -> None:
        if collection is not None:
            self._col = collection
        else:
            try:
                self._col = get_collection("embedding_cache")
            except Exception:
                self._col = None

    async def get_cached_embeddings(
        self,
        model: str,
        content_hashes: list[str],
    ) -> dict[str, list[float]]:
        """Retrieves cached chunk embeddings by content_hash."""
        if not content_hashes or self._col is None:
            return {}
        try:
            ids = [f"{model}:{ch}" for ch in content_hashes]
            cursor = self._col.find({"_id": {"$in": ids}})
            docs = await cursor.to_list(length=len(ids))
            return {doc["content_hash"]: doc["vector"] for doc in docs if "vector" in doc}
        except Exception:
            return {}

    async def save_embeddings(
        self,
        model: str,
        items: list[tuple[str, list[float]]],  # (content_hash, vector)
    ) -> None:
        """Persists newly computed chunk embeddings into the cache."""
        if not items or self._col is None:
            return
        try:
            ops = []
            for ch, vec in items:
                doc_id = f"{model}:{ch}"
                ops.append(
                    UpdateOne(
                        {"_id": doc_id},
                        {
                            "$set": {
                                "_id": doc_id,
                                "model": model,
                                "content_hash": ch,
                                "vector": vec,
                            }
                        },
                        upsert=True,
                    )
                )
            await self._col.bulk_write(ops, ordered=False)
        except Exception:
            pass

    async def get_cached_query_vector(self, model: str, query: str) -> list[float] | None:
        """Retrieves query embedding from Redis cache."""
        try:
            redis = get_redis_client()
            q_hash = hashlib.sha256(query.encode("utf-8")).hexdigest()
            key = f"embed:query:{model}:{q_hash}"
            val = await redis.get(key)
            if val:
                return json.loads(val)
        except Exception:
            pass
        return None

    async def cache_query_vector(
        self, model: str, query: str, vector: list[float], ttl_seconds: int = 3600
    ) -> None:
        """Caches query embedding in Redis with TTL (default 1 hour)."""
        try:
            redis = get_redis_client()
            q_hash = hashlib.sha256(query.encode("utf-8")).hexdigest()
            key = f"embed:query:{model}:{q_hash}"
            await redis.set(key, json.dumps(vector), ex=ttl_seconds)
        except Exception:
            pass

from __future__ import annotations

import hashlib
import json
import re
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = structlog.get_logger(__name__)


def build_answer_cache_key(
    repo_id: str,
    commit_sha: str,
    embedding_model: str,
    strategy: str,
    prompt_version: str,
    question: str,
) -> str:
    """Builds SHA-256 cache key for answer caching (§9.9)."""
    # Normalise question: lowercase, remove punctuation, collapse whitespace
    q_norm = re.sub(r"[^\w\s]", "", question.lower()).strip()
    q_norm = re.sub(r"\s+", " ", q_norm)

    raw_payload = f"{repo_id}:{commit_sha}:{embedding_model}:{strategy}:{prompt_version}:{q_norm}"
    key_hash = hashlib.sha256(raw_payload.encode("utf-8")).hexdigest()
    return f"cache:answer:{key_hash}"


class AnswerCache:
    """Redis-backed answer cache for first-turn responses (§9.9)."""

    def __init__(self, redis_client: Redis | None, ttl_seconds: int = 86400) -> None:
        self.redis = redis_client
        self.ttl = ttl_seconds

    async def get(self, cache_key: str) -> dict[str, Any] | None:
        if not self.redis:
            return None
        try:
            val = await self.redis.get(cache_key)
            if val:
                return json.loads(val)
        except Exception as e:
            logger.warning("answer_cache_get_error", error=str(e), key=cache_key)
        return None

    async def set(self, cache_key: str, data: dict[str, Any]) -> None:
        if not self.redis:
            return
        try:
            val_str = json.dumps(data)
            await self.redis.set(cache_key, val_str, ex=self.ttl)
        except Exception as e:
            logger.warning("answer_cache_set_error", error=str(e), key=cache_key)

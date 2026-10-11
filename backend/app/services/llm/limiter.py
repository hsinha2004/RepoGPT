from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = structlog.get_logger(__name__)


class LLMLimiter:
    """Manages shared concurrency and rate limits (RPM) across LLM calls (§7.6, §9.7)."""

    def __init__(
        self,
        provider: str,
        max_rpm: int = 10,
        max_concurrency: int = 4,
        redis_client: Redis | None = None,
    ) -> None:
        self.provider = provider
        self.max_rpm = max_rpm
        self.max_concurrency = max_concurrency
        self.redis_client = redis_client
        self._semaphore = asyncio.Semaphore(max_concurrency)

    @asynccontextmanager
    async def acquire(self):
        """Acquires a concurrency slot and respects RPM limits via bounded wait."""
        # 1. Concurrency limit
        async with self._semaphore:
            # 2. RPM sliding window limiter
            if self.redis_client is not None and self.max_rpm > 0:
                await self._wait_for_rpm_slot()
            yield

    async def _wait_for_rpm_slot(self) -> None:
        """Checks Redis for RPM limit and waits if needed (bounded)."""
        if not self.redis_client:
            return

        key = f"llm:rpm:{self.provider}"
        now = time.time()
        window_start = now - 60.0
        max_wait_seconds = 60.0
        start_wait = time.time()

        while time.time() - start_wait < max_wait_seconds:
            try:
                # Remove timestamps older than 60s
                pipe = self.redis_client.pipeline()
                pipe.zremrangebyscore(key, 0, window_start)
                pipe.zcard(key)
                results = await pipe.execute()
                count = results[1]

                if count < self.max_rpm:
                    # Slot available: add timestamp and set TTL
                    now_ms = time.time()
                    pipe2 = self.redis_client.pipeline()
                    pipe2.zadd(key, {str(now_ms): now_ms})
                    pipe2.expire(key, 65)
                    await pipe2.execute()
                    return

                # Limit reached: wait short interval
                await asyncio.sleep(1.0)
                now = time.time()
                window_start = now - 60.0
            except Exception as e:
                logger.warning("llm_limiter_redis_error", error=str(e))
                # On redis failure, fail-open to avoid stalling
                return

        logger.warning("llm_limiter_timeout_exceeded", provider=self.provider)

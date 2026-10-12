"""
Sliding-window rate limiter backed by Redis.
"""

import time
from collections.abc import Callable
from typing import Any

import structlog
from fastapi import Request

from app.core.errors import RateLimitedError
from app.db.redis import get_redis

logger = structlog.get_logger(__name__)


def get_client_ip(request: Request) -> str:
    """Extract client IP handling forwarded headers."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return str(forwarded.split(",")[0].strip())
    client = request.client
    return str(client.host) if client else "127.0.0.1"


async def check_sliding_window_limit(
    key: str,
    limit: int,
    window_seconds: int = 60,
) -> None:
    """
    Sliding window rate limit implementation in Redis using a sorted set.
    Key pattern: rl:{key}
    """
    try:
        redis = get_redis()
    except Exception:
        # If Redis is not available, allow request and log warning
        return

    now = time.time()
    cutoff = now - window_seconds
    pipe = redis.pipeline()

    # Remove timestamps older than the window
    pipe.zremrangebyscore(key, 0, cutoff)
    # Add current timestamp
    pipe.zadd(key, {str(now): now})
    # Count requests in window
    pipe.zcard(key)
    # Set TTL
    pipe.expire(key, window_seconds + 5)

    try:
        results = await pipe.execute()
        current_count = results[2]
        if current_count > limit:
            logger.warning("rate_limit_exceeded", key=key, count=current_count, limit=limit)
            raise RateLimitedError(
                message=f"Rate limit exceeded ({limit} requests per minute)",
                retry_after=window_seconds,
            )
    except RateLimitedError:
        raise
    except Exception as e:
        logger.warning("rate_limiter_redis_error", error=str(e))


def rate_limit(limit_func: Callable[[Request], int], scope: str) -> Callable[[Request], Any]:
    """Dependency factory for rate limiting."""

    async def dependency(request: Request) -> None:
        limit = limit_func(request)
        if scope in ("ip", "auth"):
            client_id = get_client_ip(request)
        else:
            # per-user scope
            user = getattr(request.state, "user", None)
            client_id = str(user.get("_id")) if user else get_client_ip(request)

        key = f"rl:{scope}:{client_id}"
        await check_sliding_window_limit(key, limit=limit, window_seconds=60)

    return dependency

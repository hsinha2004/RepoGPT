"""
Redis async client management and utilities.
"""

import redis.asyncio as aioredis
import structlog

from app.core.config import get_settings

logger = structlog.get_logger(__name__)

_redis_client: aioredis.Redis | None = None


async def init_redis() -> aioredis.Redis:
    """Initialize singleton Redis client connected to db 1 (cache & limits)."""
    global _redis_client
    if _redis_client is None:
        settings = get_settings()
        url = settings.get_redis_url(db=1)
        logger.info("connecting_redis", host=settings.REDIS_HOST, port=settings.REDIS_PORT)
        _redis_client = aioredis.from_url(
            url,
            encoding="utf-8",
            decode_responses=True,
            socket_timeout=5.0,
            socket_connect_timeout=5.0,
        )
    return _redis_client


async def close_redis() -> None:
    """Close Redis connection pool."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None
        logger.info("closed_redis_connection")


def get_redis() -> aioredis.Redis:
    if _redis_client is None:
        raise RuntimeError("Redis client not initialized. Call init_redis() first.")
    return _redis_client


get_redis_client = get_redis


async def ping_redis() -> bool:
    """Ping Redis to test connectivity."""
    try:
        client = get_redis()
        return bool(await client.ping())
    except Exception as e:
        logger.warning("redis_ping_failed", error=str(e))
        return False

"""
Asynchronous worker runtime for Celery tasks (§8.12).
Creates isolated event loops and fresh MongoDB / Redis clients per task invocation,
preventing cross-loop connection leakage.
"""

import asyncio
from typing import Any, TypeVar

import redis.asyncio as aioredis
import structlog
from pymongo import AsyncMongoClient

from app.core.config import get_settings
from app.db import mongo, redis

logger = structlog.get_logger(__name__)

T = TypeVar("T")


async def _execute_with_isolated_clients(coro_fn: Any, *args: Any, **kwargs: Any) -> Any:
    """Initializes dedicated async clients for the duration of this task, runs coroutine, and closes them."""
    settings = get_settings()

    # Create task-scoped MongoDB client
    mongo_client: AsyncMongoClient[dict[str, Any]] = AsyncMongoClient(
        settings.get_mongodb_uri(), serverSelectionTimeoutMS=5000
    )
    mongo._mongo_client = mongo_client

    # Create task-scoped Redis client
    redis_client = aioredis.from_url(
        settings.get_redis_url(db=1),
        encoding="utf-8",
        decode_responses=True,
    )
    redis._redis_client = redis_client

    try:
        return await coro_fn(*args, **kwargs)
    finally:
        try:
            await mongo_client.close()
        except Exception:
            pass
        try:
            await redis_client.close()
        except Exception:
            pass
        mongo._mongo_client = None
        redis._redis_client = None


def run_async_job(coro_fn: Any, *args: Any, **kwargs: Any) -> Any:
    """Synchronous entry point called by Celery tasks."""
    return asyncio.run(_execute_with_isolated_clients(coro_fn, *args, **kwargs))

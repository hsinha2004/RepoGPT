"""
Daily per-user quota tracking using Redis counters expiring at 00:00 UTC.
"""

from datetime import UTC, datetime, timedelta

import structlog

from app.core.config import get_settings
from app.core.errors import QuotaExceededError
from app.db.redis import get_redis

logger = structlog.get_logger(__name__)


def get_seconds_until_midnight_utc() -> int:
    """Calculate remaining seconds until 00:00 UTC."""
    now = datetime.now(UTC)
    tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return int((tomorrow - now).total_seconds())


async def check_and_consume_quota(
    user_id: str,
    kind: str,
    amount: int = 1,
    limit: int | None = None,
) -> None:
    """
    Check and increment user daily quota in Redis.
    Key format: quota:{user_id}:{kind}:{YYYYMMDD}
    """
    settings = get_settings()
    if limit is None:
        defaults: dict[str, int] = {
            "questions": settings.DEFAULT_QUOTA_QUESTIONS_PER_DAY,
            "ingestions": settings.DEFAULT_QUOTA_INGESTIONS_PER_DAY,
            "reviews": settings.DEFAULT_QUOTA_REVIEWS_PER_DAY,
            "tokens": settings.DEFAULT_QUOTA_TOKENS_PER_DAY,
        }
        limit = defaults.get(kind, 1000)

    try:
        redis = get_redis()
    except Exception:
        return

    now_utc = datetime.now(UTC)
    date_str = now_utc.strftime("%Y%m%d")
    key = f"quota:{user_id}:{kind}:{date_str}"

    ttl = get_seconds_until_midnight_utc()
    pipe = redis.pipeline()
    pipe.incrby(key, amount)
    pipe.expire(key, ttl + 60)

    try:
        results = await pipe.execute()
        current_val = results[0]
        if current_val > limit:
            reset_at = (now_utc + timedelta(seconds=ttl)).isoformat()
            logger.warning(
                "quota_exceeded", user_id=user_id, kind=kind, current=current_val, limit=limit
            )
            raise QuotaExceededError(
                message=f"Daily {kind} quota exceeded (Limit: {limit}). Resets at 00:00 UTC.",
                reset_at=reset_at,
            )
    except QuotaExceededError:
        raise
    except Exception as e:
        logger.warning("quota_redis_error", error=str(e))

"""
MongoDB async client management and idempotent index creation using PyMongo AsyncMongoClient.
"""

import structlog
from pymongo import ASCENDING, DESCENDING, AsyncMongoClient
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.asynchronous.database import AsyncDatabase

from app.core.config import get_settings

logger = structlog.get_logger(__name__)

_mongo_client: AsyncMongoClient | None = None


async def init_mongo() -> AsyncMongoClient:
    """Initialize singleton MongoDB AsyncClient."""
    global _mongo_client
    if _mongo_client is None:
        settings = get_settings()
        uri = settings.get_mongodb_uri()
        logger.info(
            "connecting_mongodb",
            uri=settings.MONGODB_URI or f"{settings.MONGO_HOST}:{settings.MONGO_PORT}",
        )
        _mongo_client = AsyncMongoClient(uri, serverSelectionTimeoutMS=5000)
    return _mongo_client


async def close_mongo() -> None:
    """Close MongoDB connection pool."""
    global _mongo_client
    if _mongo_client is not None:
        await _mongo_client.close()
        _mongo_client = None
        logger.info("closed_mongodb_connection")


def get_mongo_client() -> AsyncMongoClient:
    if _mongo_client is None:
        raise RuntimeError("MongoDB client not initialized. Call init_mongo() first.")
    return _mongo_client


def get_database() -> AsyncDatabase:
    client = get_mongo_client()
    settings = get_settings()
    return client[settings.MONGODB_DB]


# Collection accessors
def get_collection(name: str) -> AsyncCollection:
    return get_database()[name]


async def ping_mongo() -> bool:
    """Ping MongoDB server to check connectivity."""
    try:
        client = get_mongo_client()
        await client.admin.command("ping")
        return True
    except Exception as e:
        logger.warning("mongodb_ping_failed", error=str(e))
        return False


async def ensure_indexes() -> None:
    """
    Ensure all MongoDB indexes defined in §6.2 exist idempotently.
    """
    db = get_database()
    logger.info("ensuring_mongodb_indexes")

    # 1. users
    await db.users.create_index([("email", ASCENDING)], unique=True)
    await db.users.create_index([("github.id", ASCENDING)], unique=True, sparse=True)

    # 2. sessions
    await db.sessions.create_index([("token_hash", ASCENDING)], unique=True)
    await db.sessions.create_index([("expires_at", ASCENDING)], expireAfterSeconds=0)
    await db.sessions.create_index([("user_id", ASCENDING)])

    # 3. repositories
    await db.repositories.create_index([("owner_id", ASCENDING), ("created_at", DESCENDING)])
    await db.repositories.create_index([("source.owner", ASCENDING), ("source.name", ASCENDING)])

    # 4. repo_members
    await db.repo_members.create_index(
        [("repo_id", ASCENDING), ("user_id", ASCENDING)], unique=True
    )
    await db.repo_members.create_index([("user_id", ASCENDING)])

    # 5. jobs
    await db.jobs.create_index([("repo_id", ASCENDING), ("created_at", DESCENDING)])
    await db.jobs.create_index([("status", ASCENDING), ("created_at", ASCENDING)])
    await db.jobs.create_index([("user_id", ASCENDING)])

    # 6. files
    await db.files.create_index([("repo_id", ASCENDING), ("path", ASCENDING)], unique=True)
    await db.files.create_index([("repo_id", ASCENDING), ("metrics.pagerank", DESCENDING)])

    # 7. skipped_files
    await db.skipped_files.create_index([("repo_id", ASCENDING)])

    # 8. symbols
    await db.symbols.create_index([("repo_id", ASCENDING), ("name_lower", ASCENDING)])
    await db.symbols.create_index([("repo_id", ASCENDING), ("qualified_name", ASCENDING)])
    await db.symbols.create_index([("repo_id", ASCENDING), ("path", ASCENDING)])

    # 9. chunks
    await db.chunks.create_index([("repo_id", ASCENDING), ("path", ASCENDING)])
    await db.chunks.create_index([("repo_id", ASCENDING), ("chunk_type", ASCENDING)])

    # 10. graph_edges
    await db.graph_edges.create_index([("repo_id", ASCENDING), ("source", ASCENDING)])
    await db.graph_edges.create_index([("repo_id", ASCENDING), ("target", ASCENDING)])

    # 11. repo_overviews
    await db.repo_overviews.create_index(
        [("repo_id", ASCENDING), ("commit_sha", ASCENDING)], unique=True
    )

    # 12. conversations
    await db.conversations.create_index(
        [("user_id", ASCENDING), ("repo_id", ASCENDING), ("updated_at", DESCENDING)]
    )

    # 13. messages
    await db.messages.create_index([("conversation_id", ASCENDING), ("created_at", ASCENDING)])
    await db.messages.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])

    # 14. benchmarks
    await db.benchmarks.create_index([("name", ASCENDING)], unique=True)

    # 15. eval_runs
    await db.eval_runs.create_index([("created_at", DESCENDING)])
    await db.eval_runs.create_index([("repo_id", ASCENDING)])

    # 16. eval_results
    await db.eval_results.create_index([("run_id", ASCENDING), ("strategy", ASCENDING)])

    # 17. reviews
    await db.reviews.create_index([("repo_id", ASCENDING), ("created_at", DESCENDING)])

    # 18. review_findings
    await db.review_findings.create_index([("review_id", ASCENDING)])
    await db.review_findings.create_index([("repo_id", ASCENDING), ("status", ASCENDING)])

    # 19. usage_events (TTL: 365 days = 31536000s)
    await db.usage_events.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
    await db.usage_events.create_index([("created_at", ASCENDING)], expireAfterSeconds=31536000)

    # 20. audit_logs (TTL: 180 days = 15552000s)
    await db.audit_logs.create_index([("actor_id", ASCENDING), ("created_at", DESCENDING)])
    await db.audit_logs.create_index([("created_at", ASCENDING)], expireAfterSeconds=15552000)

    # 21. webhook_deliveries (TTL: 30 days = 2592000s)
    await db.webhook_deliveries.create_index([("delivery_id", ASCENDING)], unique=True)
    await db.webhook_deliveries.create_index(
        [("received_at", ASCENDING)], expireAfterSeconds=2592000
    )

    logger.info("mongodb_indexes_ensured_successfully")

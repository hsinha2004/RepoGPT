"""
Health check endpoints (/live and /ready).
"""

import time

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.db.mongo import ping_mongo
from app.db.redis import ping_redis
from app.schemas.common import HealthComponentStatus, HealthLiveResponse, HealthReadyResponse

router = APIRouter(prefix="/health", tags=["Health"])

_cached_ready_status: dict[str, HealthComponentStatus] = {}
_cached_ready_timestamp: float = 0.0


@router.get("/live", response_model=HealthLiveResponse, summary="Liveness probe")
async def live() -> HealthLiveResponse:
    """Liveness probe: verifies process is running."""
    settings = get_settings()
    return HealthLiveResponse(status="ok", app=settings.APP_NAME, version="0.1.0")


@router.get("/ready", response_model=HealthReadyResponse, summary="Readiness probe")
async def ready() -> JSONResponse:
    """
    Readiness probe: checks MongoDB, Redis, vector store configuration,
    and LLM setup (cached for 60s, no paid LLM call).
    """
    global _cached_ready_status, _cached_ready_timestamp
    settings = get_settings()
    now = time.time()

    # Cache results for 60s to prevent overloading services
    if now - _cached_ready_timestamp < 60.0 and _cached_ready_status:
        components = _cached_ready_status
    else:
        components = {}

        # 1. MongoDB check
        mongo_ok = await ping_mongo()
        components["mongodb"] = HealthComponentStatus(
            status="ok" if mongo_ok else "down",
            message="Connected" if mongo_ok else "Cannot connect to MongoDB",
        )

        # 2. Redis check
        redis_ok = await ping_redis()
        components["redis"] = HealthComponentStatus(
            status="ok" if redis_ok else "down",
            message="Connected" if redis_ok else "Cannot connect to Redis",
        )

        # 3. Vector store check
        components["vector_store"] = HealthComponentStatus(
            status="ok",
            message=f"Configured vector store: {settings.VECTOR_STORE}",
        )

        # 4. LLM provider configuration check
        llm_status = (
            "ok" if (settings.LLM_PROVIDER == "fake" or bool(settings.LLM_API_KEY)) else "degraded"
        )
        llm_msg = f"Provider: {settings.LLM_PROVIDER}" + (
            " (key present)" if settings.LLM_API_KEY else " (offline/fake mode)"
        )
        components["llm"] = HealthComponentStatus(
            status=llm_status,
            message=llm_msg,
        )

        # 5. Embedding check
        components["embeddings"] = HealthComponentStatus(
            status="ok",
            message=f"Provider: {settings.EMBEDDING_PROVIDER}, Model: {settings.EMBEDDING_MODEL}",
        )

        _cached_ready_status = components
        _cached_ready_timestamp = now

    is_down = any(c.status == "down" for c in components.values())
    is_degraded = any(c.status == "degraded" for c in components.values())

    overall_status = "down" if is_down else ("degraded" if is_degraded else "ok")
    http_status = status.HTTP_503_SERVICE_UNAVAILABLE if is_down else status.HTTP_200_OK

    return JSONResponse(
        status_code=http_status,
        content={
            "status": overall_status,
            "components": {k: v.model_dump() for k, v in components.items()},
        },
    )

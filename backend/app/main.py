"""
FastAPI application entrypoint and lifespan management.
"""

import time
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_v1_router
from app.core.config import get_settings
from app.core.errors import (
    AppError,
    app_error_handler,
    unhandled_exception_handler,
    validation_error_handler,
)
from app.core.logging import setup_logging
from app.core.security import hash_password
from app.db.mongo import close_mongo, ensure_indexes, get_database, init_mongo, ping_mongo
from app.db.redis import close_redis, init_redis, ping_redis

logger = structlog.get_logger(__name__)


async def seed_initial_admin() -> None:
    """Ensure at least one admin account exists."""
    settings = get_settings()
    try:
        db = get_database()
        existing_admin = await db.users.find_one({"role": "admin"})
        if not existing_admin and settings.ADMIN_EMAIL and settings.ADMIN_PASSWORD:
            admin_doc = {
                "email": settings.ADMIN_EMAIL.lower(),
                "name": "RepoGPT Administrator",
                "password_hash": hash_password(settings.ADMIN_PASSWORD),
                "role": "admin",
                "is_active": True,
                "must_change_password": False,
                "failed_login_count": 0,
                "locked_until": None,
                "created_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC),
            }
            await db.users.insert_one(admin_doc)
            logger.info("seeded_initial_admin_user", email=settings.ADMIN_EMAIL)
    except Exception as e:
        logger.warning("seed_admin_skipped_or_failed", error=str(e))


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context: initialize and teardown resources."""
    setup_logging()
    settings = get_settings()
    logger.info("starting_repogpt", environment=settings.ENVIRONMENT, app_name=settings.APP_NAME)

    # Initialize Databases
    try:
        await init_mongo()
        if await ping_mongo():
            await ensure_indexes()
            await seed_initial_admin()
    except Exception as e:
        logger.warning("mongodb_init_warning", error=str(e))

    try:
        await init_redis()
        await ping_redis()
    except Exception as e:
        logger.warning("redis_init_warning", error=str(e))

    yield

    # Teardown
    logger.info("shutting_down_repogpt")
    await close_redis()
    await close_mongo()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    settings = get_settings()

    docs_url = "/api/docs" if settings.EXPOSE_API_DOCS else None
    redoc_url = "/api/redoc" if settings.EXPOSE_API_DOCS else None
    openapi_url = "/api/openapi.json" if settings.EXPOSE_API_DOCS else None

    app = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
        lifespan=lifespan,
    )

    # 1. CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list or ["http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 2. Security Headers & Request ID Middleware
    @app.middleware("http")
    async def request_middleware(request: Request, call_next) -> Response:
        # Request ID handling
        incoming_req_id = request.headers.get("X-Request-ID")
        request_id = incoming_req_id if incoming_req_id else uuid.uuid4().hex
        request.state.request_id = request_id

        # Bind logging context
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        start_time = time.perf_counter()
        response: Response = await call_next(request)
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # Set Security Headers (§11.11)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"

        if settings.ENVIRONMENT == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        logger.info(
            "http_request_finished",
            status_code=response.status_code,
            latency_ms=latency_ms,
        )
        return response

    # 3. Exception Handlers
    app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_exception_handler)

    # 4. Mount API v1 Routers
    app.include_router(api_v1_router)

    return app


app = create_app()

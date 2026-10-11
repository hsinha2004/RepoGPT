"""
Structured logging with structlog, secret scrubbing, and request context binding.
"""

import logging
import re
import sys
from typing import Any

import structlog

from app.core.config import get_settings

SENSITIVE_KEYS = {
    "authorization",
    "cookie",
    "password",
    "token",
    "secret",
    "api_key",
    "github_token",
    "pat",
    "access_token",
    "refresh_token",
    "rg_refresh",
    "rg_csrf",
}

SECRET_PATTERN = re.compile(
    r"(ghp_[A-Za-z0-9_]{36}|github_pat_[A-Za-z0-9_]{82}|sk-[A-Za-z0-9]{32,}|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z-_]{35})"
)


def scrub_secrets(_logger: Any, _method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    """Scrub sensitive keys and secret patterns from logging event dict."""
    for key, value in list(event_dict.items()):
        lower_key = str(key).lower()
        if any(sensitive in lower_key for sensitive in SENSITIVE_KEYS):
            event_dict[key] = "<REDACTED>"
        elif isinstance(value, str):
            event_dict[key] = SECRET_PATTERN.sub("<REDACTED_SECRET>", value)
    return event_dict


def setup_logging() -> None:
    settings = get_settings()
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        scrub_secrets,
    ]

    formatter: Any = (
        structlog.processors.JSONRenderer()
        if (settings.LOG_FORMAT == "json" or settings.ENVIRONMENT == "production")
        else structlog.dev.ConsoleRenderer(colors=True)
    )

    structlog.configure(
        processors=shared_processors
        + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            foreign_pre_chain=shared_processors,
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                formatter,
            ],
        )
    )

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(log_level)

    # Silence overly verbose third-party loggers
    for lib in ("uvicorn.access", "urllib3", "httpx", "httpcore"):
        logging.getLogger(lib).setLevel(logging.WARNING)

"""
Error hierarchy and standardized error envelope formatting.
"""

from typing import Any

import structlog
from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = structlog.get_logger(__name__)


class AppError(Exception):
    """Base class for all RepoGPT application errors."""

    def __init__(
        self,
        message: str = "An application error occurred",
        code: str = "APP_ERROR",
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        self.headers = headers or {}


class BadRequestError(AppError):
    def __init__(
        self,
        message: str = "Bad request",
        code: str = "BAD_REQUEST",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            code=code,
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
        )


class NotFoundError(AppError):
    def __init__(
        self,
        message: str = "Resource not found",
        code: str = "NOT_FOUND",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            code=code, message=message, status_code=status.HTTP_404_NOT_FOUND, details=details
        )


class UnauthorizedError(AppError):
    def __init__(
        self,
        message: str = "Authentication required",
        code: str = "UNAUTHORIZED",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            code=code, message=message, status_code=status.HTTP_401_UNAUTHORIZED, details=details
        )


class ForbiddenError(AppError):
    def __init__(
        self,
        message: str = "Access forbidden",
        code: str = "FORBIDDEN",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            code=code, message=message, status_code=status.HTTP_403_FORBIDDEN, details=details
        )


class ConflictError(AppError):
    def __init__(
        self,
        message: str = "Resource conflict",
        code: str = "CONFLICT",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            code=code, message=message, status_code=status.HTTP_409_CONFLICT, details=details
        )


HTTP_422 = getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422)


class ValidationFailedError(AppError):
    def __init__(
        self,
        message: str = "Validation failed",
        code: str = "VALIDATION_FAILED",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(code=code, message=message, status_code=HTTP_422, details=details)


class RateLimitedError(AppError):
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: int = 60,
        details: dict[str, Any] | None = None,
    ):
        headers = {"Retry-After": str(retry_after)}
        details = details or {}
        details["retry_after"] = retry_after
        super().__init__(
            code="RATE_LIMITED",
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details=details,
            headers=headers,
        )


class QuotaExceededError(AppError):
    def __init__(
        self,
        message: str = "Quota exceeded",
        reset_at: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        details = details or {}
        if reset_at:
            details["reset_at"] = reset_at
        super().__init__(
            code="QUOTA_EXCEEDED",
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details=details,
        )


class UpstreamError(AppError):
    def __init__(
        self,
        message: str = "Upstream service error",
        code: str = "UPSTREAM_ERROR",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            code=code, message=message, status_code=status.HTTP_502_BAD_GATEWAY, details=details
        )


class PayloadTooLargeError(AppError):
    def __init__(
        self,
        message: str = "Payload too large",
        code: str = "PAYLOAD_TOO_LARGE",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            code=code,
            message=message,
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            details=details,
        )


def format_error_response(
    code: str,
    message: str,
    status_code: int,
    request_id: str,
    details: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    content = {
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
            "request_id": request_id,
        }
    }
    return JSONResponse(status_code=status_code, content=content, headers=headers)


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    logger.warning(
        "app_error",
        code=exc.code,
        message=exc.message,
        status_code=exc.status_code,
        request_id=request_id,
    )
    return format_error_response(
        code=exc.code,
        message=exc.message,
        status_code=exc.status_code,
        request_id=request_id,
        details=exc.details,
        headers=exc.headers,
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    field_errors = []
    for err in exc.errors():
        field_errors.append(
            {"loc": err.get("loc", []), "msg": err.get("msg", ""), "type": err.get("type", "")}
        )
    logger.warning("validation_error", errors=field_errors, request_id=request_id)
    return format_error_response(
        code="VALIDATION_FAILED",
        message="Request validation failed",
        status_code=HTTP_422,
        request_id=request_id,
        details={"fields": field_errors},
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error("unhandled_exception", error=str(exc), exc_info=True, request_id=request_id)
    return format_error_response(
        code="INTERNAL_SERVER_ERROR",
        message="An unexpected internal server error occurred",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        request_id=request_id,
        details={},
    )

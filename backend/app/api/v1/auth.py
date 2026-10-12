"""
Authentication endpoints: register, login, refresh rotation, logout, and me.
"""

from typing import Any

from fastapi import APIRouter, Cookie, Depends, Header, Request, Response

from app.core.config import get_settings
from app.core.deps import get_current_user
from app.core.rate_limit import get_client_ip, rate_limit
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.services.auth.service import AuthService, get_auth_service

router = APIRouter(prefix="/auth", tags=["Auth"])


def format_user_response(user: dict[str, Any]) -> UserResponse:
    return UserResponse(
        id=str(user["_id"]),
        email=user["email"],
        name=user["name"],
        role=user.get("role", "user"),
        is_active=user.get("is_active", True),
        has_pat=bool(user.get("github_pat_encrypted")),
        pat_last4=user.get("github_pat_last4"),
        must_change_password=user.get("must_change_password", False),
        created_at=user["created_at"],
    )


def set_auth_cookies(response: Response, refresh_token: str, csrf_token: str) -> None:
    settings = get_settings()
    max_age = settings.REFRESH_TTL_DAYS * 86400

    # HttpOnly refresh cookie (§7.4)
    response.set_cookie(
        key="rg_refresh",
        value=refresh_token,
        max_age=max_age,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        path="/api/v1/auth",
    )

    # Non-HttpOnly CSRF cookie for double-submit header (§7.4)
    response.set_cookie(
        key="rg_csrf",
        value=csrf_token,
        max_age=max_age,
        httponly=False,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        path="/",
    )


def clear_auth_cookies(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        key="rg_refresh", path="/api/v1/auth", secure=settings.COOKIE_SECURE, samesite="lax"
    )
    response.delete_cookie(
        key="rg_csrf", path="/", secure=settings.COOKIE_SECURE, samesite="lax"
    )


@router.post(
    "/register",
    response_model=TokenResponse,
    dependencies=[Depends(rate_limit(lambda _: 10, scope="auth"))],
    summary="Register account",
)
async def register(
    req: RegisterRequest,
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    ip = get_client_ip(request)
    ua = request.headers.get("user-agent", "")
    access_token, refresh_token, csrf_token, user = await auth_service.register(
        email=req.email,
        name=req.name,
        password=req.password,
        ip=ip,
        user_agent=ua,
    )
    set_auth_cookies(response, refresh_token, csrf_token)
    return TokenResponse(access_token=access_token, user=format_user_response(user))


@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(rate_limit(lambda _: 10, scope="auth"))],
    summary="User login",
)
async def login(
    req: LoginRequest,
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    ip = get_client_ip(request)
    ua = request.headers.get("user-agent", "")
    access_token, refresh_token, csrf_token, user = await auth_service.login(
        email=req.email,
        password=req.password,
        ip=ip,
        user_agent=ua,
    )
    set_auth_cookies(response, refresh_token, csrf_token)
    return TokenResponse(access_token=access_token, user=format_user_response(user))


@router.post("/refresh", response_model=TokenResponse, summary="Rotate refresh token")
async def refresh(
    request: Request,
    response: Response,
    rg_refresh: str | None = Cookie(default=None),
    rg_csrf: str | None = Cookie(default=None),
    x_csrf_token: str | None = Header(default=None),
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    ip = get_client_ip(request)
    ua = request.headers.get("user-agent", "")
    if not rg_refresh:
        from app.core.errors import UnauthorizedError

        raise UnauthorizedError("Missing refresh token cookie")

    access_token, new_refresh, new_csrf, user = await auth_service.refresh(
        raw_refresh_token=rg_refresh,
        csrf_header=x_csrf_token or "",
        csrf_cookie=rg_csrf or "",
        ip=ip,
        user_agent=ua,
    )
    set_auth_cookies(response, new_refresh, new_csrf)
    return TokenResponse(access_token=access_token, user=format_user_response(user))


@router.post("/logout", summary="Log out current session")
async def logout(
    response: Response,
    user: dict[str, Any] = Depends(get_current_user),
    rg_refresh: str | None = Cookie(default=None),
    auth_service: AuthService = Depends(get_auth_service),
) -> dict[str, str]:
    if rg_refresh:
        await auth_service.logout(rg_refresh, str(user["_id"]))
    clear_auth_cookies(response)
    return {"message": "Successfully logged out"}


@router.post("/logout-all", summary="Log out of all devices")
async def logout_all(
    response: Response,
    user: dict[str, Any] = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> dict[str, str]:
    await auth_service.logout_all(str(user["_id"]))
    clear_auth_cookies(response)
    return {"message": "Successfully revoked all sessions"}


@router.get("/me", response_model=UserResponse, summary="Get current user profile")
async def get_me(user: dict[str, Any] = Depends(get_current_user)) -> UserResponse:
    return format_user_response(user)

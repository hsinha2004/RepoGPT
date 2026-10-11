"""
User account management endpoints (profile, password, PAT, deletion, usage).
"""

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Response

from app.core.config import get_settings
from app.core.deps import get_current_user
from app.core.quotas import get_seconds_until_midnight_utc
from app.schemas.auth import (
    ChangePasswordRequest,
    PatStatusResponse,
    SetPatRequest,
    UpdateProfileRequest,
    UsageQuotaItem,
    UserResponse,
    UserUsageResponse,
)
from app.services.users.service import UserService, get_user_service

router = APIRouter(prefix="/users", tags=["Users"])


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


@router.patch("/me", response_model=UserResponse, summary="Update user profile")
async def update_profile(
    req: UpdateProfileRequest,
    user: dict[str, Any] = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
) -> UserResponse:
    updated = await user_service.update_profile(str(user["_id"]), req.name)
    return format_user_response(updated)


@router.post("/me/password", summary="Change user password")
async def change_password(
    req: ChangePasswordRequest,
    user: dict[str, Any] = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
) -> dict[str, str]:
    await user_service.change_password(str(user["_id"]), req.current_password, req.new_password)
    return {"message": "Password updated successfully"}


@router.delete("/me", summary="Delete user account and all owned assets")
async def delete_account(
    response: Response,
    user: dict[str, Any] = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
) -> dict[str, str]:
    await user_service.delete_account(str(user["_id"]))
    settings = get_settings()
    response.delete_cookie(
        key="rg_refresh", path="/api/v1/auth", secure=settings.COOKIE_SECURE, samesite="strict"
    )
    response.delete_cookie(
        key="rg_csrf", path="/api/v1/auth", secure=settings.COOKIE_SECURE, samesite="strict"
    )
    return {"message": "Account successfully deleted"}


@router.put(
    "/me/github-token", response_model=PatStatusResponse, summary="Set personal access token"
)
async def set_pat(
    req: SetPatRequest,
    user: dict[str, Any] = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
) -> PatStatusResponse:
    res = await user_service.set_github_pat(str(user["_id"]), req.token)
    return PatStatusResponse(has_pat=res["has_pat"], last4=res["last4"])


@router.delete(
    "/me/github-token", response_model=PatStatusResponse, summary="Delete personal access token"
)
async def remove_pat(
    user: dict[str, Any] = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
) -> PatStatusResponse:
    res = await user_service.remove_github_pat(str(user["_id"]))
    return PatStatusResponse(has_pat=res["has_pat"], last4=res["last4"])


@router.post("/me/github-token/test", summary="Test personal access token validity")
async def test_pat(
    req: SetPatRequest,
    user_service: UserService = Depends(get_user_service),
) -> dict[str, Any]:
    return await user_service.test_github_pat(req.token)


@router.get("/me/usage", response_model=UserUsageResponse, summary="Get quotas and usage")
async def get_usage(
    _user: dict[str, Any] = Depends(get_current_user),
) -> UserUsageResponse:
    settings = get_settings()
    now_utc = datetime.now(UTC)
    seconds_until_midnight = get_seconds_until_midnight_utc()
    from datetime import timedelta

    reset_at = (now_utc + timedelta(seconds=seconds_until_midnight)).isoformat()

    quotas_map = {
        "questions": UsageQuotaItem(
            current=0, limit=settings.DEFAULT_QUOTA_QUESTIONS_PER_DAY, reset_at=reset_at
        ),
        "ingestions": UsageQuotaItem(
            current=0, limit=settings.DEFAULT_QUOTA_INGESTIONS_PER_DAY, reset_at=reset_at
        ),
        "reviews": UsageQuotaItem(
            current=0, limit=settings.DEFAULT_QUOTA_REVIEWS_PER_DAY, reset_at=reset_at
        ),
        "tokens": UsageQuotaItem(
            current=0, limit=settings.DEFAULT_QUOTA_TOKENS_PER_DAY, reset_at=reset_at
        ),
    }

    return UserUsageResponse(
        quotas=quotas_map,
        stats_today={"questions": 0, "tokens": 0, "reviews": 0},
        stats_30d={"questions": 0, "tokens": 0, "reviews": 0},
    )

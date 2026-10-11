"""
FastAPI dependency injection utilities for authentication, authorization, and repo scoping.
"""

from collections.abc import Callable
from typing import Any

from bson import ObjectId
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.errors import ForbiddenError, NotFoundError, UnauthorizedError
from app.core.security import decode_access_token
from app.db.mongo import get_database

security_bearer = HTTPBearer(auto_error=False)

ROLE_HIERARCHY = {
    "viewer": 1,
    "editor": 2,
    "owner": 3,
    "admin": 4,
}


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_bearer),
) -> dict[str, Any]:
    """Validate Bearer access token and load active user from database."""
    if not credentials or not credentials.credentials:
        raise UnauthorizedError("Missing or invalid authorization header")

    token = credentials.credentials
    payload = decode_access_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedError("Invalid token payload")

    db = get_database()
    try:
        user = await db.users.find_one({"_id": ObjectId(user_id)})
    except Exception:
        user = await db.users.find_one({"_id": user_id})

    if not user:
        raise UnauthorizedError("User account not found")

    if not user.get("is_active", True):
        raise UnauthorizedError("User account is inactive or disabled")

    return user


async def get_optional_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_bearer),
) -> dict[str, Any] | None:
    """Optional user authentication; returns None if not authenticated."""
    if not credentials or not credentials.credentials:
        return None
    try:
        return await get_current_user(credentials)
    except Exception:
        return None


def require_role(required_role: str) -> Callable[..., Any]:
    """Ensure user has at least the specified global role (user or admin)."""

    async def role_dependency(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
        user_role = user.get("role", "user")
        if required_role == "admin" and user_role != "admin":
            raise ForbiddenError("Administrator access required")
        return user

    return role_dependency


def require_repo_access(min_role: str = "viewer") -> Callable[..., Any]:
    """
    Ensure user has repository access with at least min_role (viewer, editor, owner).
    Admins automatically have access.
    Crucial Security requirement (§7.5): Missing or unauthorized repo access returns 404 NOT FOUND.
    """

    async def repo_access_dependency(
        repo_id: str,
        user: dict[str, Any] = Depends(get_current_user),
    ) -> dict[str, Any]:
        db = get_database()
        user_id = str(user["_id"])
        user_role = user.get("role", "user")

        # Find repository by ObjectId or str
        try:
            repo = await db.repositories.find_one({"_id": ObjectId(repo_id)})
        except Exception:
            repo = await db.repositories.find_one({"_id": repo_id})

        if not repo:
            raise NotFoundError("Repository not found", code="REPO_NOT_FOUND")

        # Admins have all permissions
        if user_role == "admin":
            return repo

        # Repo direct owner
        if str(repo.get("owner_id")) == user_id:
            effective_role = "owner"
        else:
            # Check membership
            member = await db.repo_members.find_one(
                {"repo_id": str(repo["_id"]), "user_id": user_id}
            )
            if not member:
                # Security §7.5: return 404, do not reveal existence
                raise NotFoundError("Repository not found", code="REPO_NOT_FOUND")
            effective_role = member.get("role", "viewer")

        min_level = ROLE_HIERARCHY.get(min_role, 1)
        user_level = ROLE_HIERARCHY.get(effective_role, 1)

        if user_level < min_level:
            # Security §7.5: 404 on insufficient permission to not reveal repo existence
            raise NotFoundError("Repository not found", code="REPO_NOT_FOUND")

        return repo

    return repo_access_dependency

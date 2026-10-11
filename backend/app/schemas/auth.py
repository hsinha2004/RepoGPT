"""
Pydantic schemas for authentication, users, sessions, and quotas.
"""

from datetime import datetime

from pydantic import EmailStr, Field

from app.schemas.common import BaseSchema


class RegisterRequest(BaseSchema):
    email: EmailStr
    name: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=10, max_length=128)


class LoginRequest(BaseSchema):
    email: EmailStr
    password: str


class UserResponse(BaseSchema):
    id: str
    email: str
    name: str
    role: str
    is_active: bool
    has_pat: bool = False
    pat_last4: str | None = None
    must_change_password: bool = False
    created_at: datetime


class TokenResponse(BaseSchema):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class UpdateProfileRequest(BaseSchema):
    name: str = Field(min_length=2, max_length=100)


class ChangePasswordRequest(BaseSchema):
    current_password: str
    new_password: str = Field(min_length=10, max_length=128)


class SetPatRequest(BaseSchema):
    token: str = Field(min_length=10, max_length=255)


class PatStatusResponse(BaseSchema):
    has_pat: bool
    last4: str | None = None


class UsageQuotaItem(BaseSchema):
    current: int
    limit: int
    reset_at: str


class UserUsageResponse(BaseSchema):
    quotas: dict[str, UsageQuotaItem]
    stats_today: dict[str, int]
    stats_30d: dict[str, int]

"""
Common Pydantic schemas, pagination models, error envelopes, and health models.
"""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class BaseSchema(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        from_attributes=True,
    )


class ErrorDetail(BaseSchema):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    request_id: str


class ErrorEnvelope(BaseSchema):
    error: ErrorDetail


class PaginationQuery(BaseSchema):
    limit: int = Field(default=20, ge=1, le=100)
    cursor: str | None = Field(default=None)


class PaginatedResponse(BaseSchema, Generic[T]):
    items: list[T]
    next_cursor: str | None = None
    total: int | None = None


class HealthLiveResponse(BaseSchema):
    status: str = "ok"
    app: str = "RepoGPT"
    version: str = "0.1.0"


class HealthComponentStatus(BaseSchema):
    status: str
    message: str | None = None


class HealthReadyResponse(BaseSchema):
    status: str  # ok | degraded | down
    components: dict[str, HealthComponentStatus]

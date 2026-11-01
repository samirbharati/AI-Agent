"""Common shared Pydantic schemas and base classes."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Base schema
# ---------------------------------------------------------------------------


class AppBaseModel(BaseModel):
    """Base model with ORM mode enabled and standard config."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------


class PaginationParams(BaseModel):
    """Query parameters for paginated list endpoints."""

    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


class PaginatedResponse(AppBaseModel, Generic[T]):
    """Generic paginated response envelope."""

    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int

    @classmethod
    def create(
        cls,
        items: list[T],
        total: int,
        pagination: PaginationParams,
    ) -> PaginatedResponse[T]:
        import math

        return cls(
            items=items,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
            total_pages=math.ceil(total / pagination.page_size) if total > 0 else 0,
        )


# ---------------------------------------------------------------------------
# Standard API responses
# ---------------------------------------------------------------------------


class StatusResponse(AppBaseModel):
    """Generic status / acknowledgment response."""

    status: str
    message: str


class ErrorDetail(AppBaseModel):
    """Structured error detail for API error responses."""

    code: str
    message: str
    field: str | None = None
    details: dict[str, Any] | None = None


class ErrorResponse(AppBaseModel):
    """Top-level error response envelope."""

    error: ErrorDetail
    request_id: str | None = None

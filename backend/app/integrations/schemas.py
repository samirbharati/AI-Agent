"""
Integration Provider schemas and data models.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class IntegrationCategory(str, Enum):
    VCS = "vcs"
    CI_CD = "ci_cd"
    SECURITY = "security"
    OBSERVABILITY = "observability"
    ERROR_TRACKING = "error_tracking"
    MONITORING = "monitoring"
    DEPLOYMENT = "deployment"
    STORAGE = "storage"
    AUTH = "auth"


class ProviderStatus(str, Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    NOT_CONFIGURED = "not_configured"
    DISABLED = "disabled"
    ERROR = "error"


class ProviderHealth(BaseModel):
    status: ProviderStatus
    message: str = "Ready"
    latency_ms: float | None = None
    last_checked: datetime = Field(default_factory=lambda: datetime.now(UTC))
    details: dict[str, Any] = Field(default_factory=dict)


class ProviderUsage(BaseModel):
    quota_used: float = 0.0
    quota_total: float | None = None
    quota_unit: str = "units"
    percentage: float | None = None
    resets_at: datetime | None = None
    description: str | None = None


class IntegrationStatusResponse(BaseModel):
    provider_id: str
    name: str
    category: IntegrationCategory
    description: str
    free_tier_info: str
    is_enabled: bool
    status: ProviderStatus
    message: str
    latency_ms: float | None = None
    last_checked: datetime
    usage: ProviderUsage | None = None
    features: list[str] = Field(default_factory=list)
    has_credentials: bool = False


class IntegrationToggleRequest(BaseModel):
    enabled: bool


class IntegrationTestResult(BaseModel):
    success: bool
    status: ProviderStatus
    message: str
    latency_ms: float | None = None
    details: dict[str, Any] = Field(default_factory=dict)

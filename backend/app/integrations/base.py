"""
Base abstract classes for external developer service integrations.
"""

from __future__ import annotations

import abc
import time

from app.integrations.schemas import (
    IntegrationCategory,
    IntegrationStatusResponse,
    IntegrationTestResult,
    ProviderHealth,
    ProviderStatus,
    ProviderUsage,
)


class IntegrationProvider(abc.ABC):
    """
    Abstract Base Class for an AgentForge free developer service integration.
    """

    @property
    @abc.abstractmethod
    def provider_id(self) -> str:
        """Unique key for the provider (e.g. 'github', 'semgrep', 'openobserve')."""

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Human-readable display name."""

    @property
    @abc.abstractmethod
    def category(self) -> IntegrationCategory:
        """Categorization of developer service."""

    @property
    @abc.abstractmethod
    def description(self) -> str:
        """Brief summary of what this service integration provides."""

    @property
    @abc.abstractmethod
    def free_tier_info(self) -> str:
        """Summary of free-tier quotas and allowances."""

    @property
    def features(self) -> list[str]:
        """List of supported feature capabilities."""
        return []

    @abc.abstractmethod
    def is_enabled(self) -> bool:
        """Whether this provider is currently enabled in config/state."""

    @abc.abstractmethod
    def has_credentials(self) -> bool:
        """Whether the minimum required credentials are configured."""

    @abc.abstractmethod
    async def check_health(self) -> ProviderHealth:
        """Perform a live or simulated connectivity probe."""

    async def get_usage(self) -> ProviderUsage | None:
        """Fetch current quota usage via provider API if available."""
        return None

    async def test_connection(self) -> IntegrationTestResult:
        """Standardized test action called from the UI."""
        start = time.perf_counter()
        try:
            health = await self.check_health()
            latency = (time.perf_counter() - start) * 1000.0
            return IntegrationTestResult(
                success=health.status == ProviderStatus.CONNECTED,
                status=health.status,
                message=health.message,
                latency_ms=latency,
                details=health.details,
            )
        except Exception as e:
            latency = (time.perf_counter() - start) * 1000.0
            return IntegrationTestResult(
                success=False,
                status=ProviderStatus.ERROR,
                message=f"Test failed: {e}",
                latency_ms=latency,
                details={"error": str(e)},
            )

    async def to_status_response(self) -> IntegrationStatusResponse:
        """Convert current provider state to API status response."""
        health = await self.check_health()
        usage = await self.get_usage()
        return IntegrationStatusResponse(
            provider_id=self.provider_id,
            name=self.name,
            category=self.category,
            description=self.description,
            free_tier_info=self.free_tier_info,
            is_enabled=self.is_enabled(),
            status=health.status,
            message=health.message,
            latency_ms=health.latency_ms,
            last_checked=health.last_checked,
            usage=usage,
            features=self.features,
            has_credentials=self.has_credentials(),
        )

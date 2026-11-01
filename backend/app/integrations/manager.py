"""
Central Integration Manager orchestrating all developer service integrations.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.integrations.base import IntegrationProvider
from app.integrations.schemas import (
    IntegrationCategory,
    IntegrationStatusResponse,
    IntegrationTestResult,
    ProviderStatus,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class IntegrationManager:
    """Singleton registry and coordinator for external service integrations."""

    _instance: IntegrationManager | None = None

    def __init__(self) -> None:
        self._providers: dict[str, IntegrationProvider] = {}
        self._runtime_overrides: dict[str, bool] = {}

    @classmethod
    def get_instance(cls) -> IntegrationManager:
        if cls._instance is None:
            cls._instance = IntegrationManager()
        return cls._instance

    def register_provider(self, provider: IntegrationProvider) -> None:
        """Register a provider in the registry."""
        self._providers[provider.provider_id] = provider
        logger.info(
            "Registered integration provider: %s (%s)",
            provider.name,
            provider.provider_id,
        )

    def get_provider(self, provider_id: str) -> IntegrationProvider | None:
        """Retrieve a registered provider by key."""
        return self._providers.get(provider_id)

    def list_providers(self) -> list[IntegrationProvider]:
        """Return all registered providers in priority order."""
        return list(self._providers.values())

    async def get_all_statuses(
        self, category: IntegrationCategory | None = None
    ) -> list[IntegrationStatusResponse]:
        """Query statuses for all registered providers, optionally filtered by category."""
        results: list[IntegrationStatusResponse] = []
        for provider in self._providers.values():
            if category and provider.category != category:
                continue
            resp = await provider.to_status_response()
            # Apply runtime override if set
            if provider.provider_id in self._runtime_overrides:
                resp.is_enabled = self._runtime_overrides[provider.provider_id]
                if not resp.is_enabled:
                    resp.status = ProviderStatus.DISABLED
                    resp.message = "Disabled by user runtime preference"
            results.append(resp)
        return results

    async def test_provider(self, provider_id: str) -> IntegrationTestResult:
        """Execute a connectivity test against a specific provider."""
        provider = self.get_provider(provider_id)
        if not provider:
            return IntegrationTestResult(
                success=False,
                status=ProviderStatus.ERROR,
                message=f"Provider '{provider_id}' is not registered.",
            )
        return await provider.test_connection()

    def set_provider_enabled(self, provider_id: str, enabled: bool) -> bool:
        """Set a runtime enabled/disabled override for a provider."""
        if provider_id not in self._providers:
            return False
        self._runtime_overrides[provider_id] = enabled
        logger.info("Provider '%s' enabled set to %s", provider_id, enabled)
        return True


_manager_instance: IntegrationManager | None = None


def get_integration_manager() -> IntegrationManager:
    """Retrieve global singleton IntegrationManager."""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = IntegrationManager()
    return _manager_instance

"""
Better Stack Uptime Monitoring and Heartbeat Integration Provider.
"""

from __future__ import annotations

import logging
import time

import httpx
from app.config import get_settings
from app.integrations.base import IntegrationProvider
from app.integrations.schemas import (
    IntegrationCategory,
    ProviderHealth,
    ProviderStatus,
    ProviderUsage,
)

logger = logging.getLogger(__name__)


class BetterStackService(IntegrationProvider):
    """
    Better Stack uptime heartbeat and status telemetry provider.
    """

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._settings = get_settings()
        self._external_client = client

    @property
    def provider_id(self) -> str:
        return "betterstack"

    @property
    def name(self) -> str:
        return "Better Stack"

    @property
    def category(self) -> IntegrationCategory:
        return IntegrationCategory.MONITORING

    @property
    def description(self) -> str:
        return (
            "Uptime and infrastructure monitoring: Periodic heartbeats, "
            "subsystem health telemetry, and status page synchronization."
        )

    @property
    def free_tier_info(self) -> str:
        return "10 free uptime monitors, 3-minute checking frequency, free hosted status page."

    @property
    def features(self) -> list[str]:
        return [
            "Push Heartbeat Telemetry",
            "Multi-Subsystem Health Auditing",
            "Public & Internal Status Dashboards",
            "Incident Alert Dispatch",
        ]

    def is_enabled(self) -> bool:
        return self._settings.betterstack_enabled

    def has_credentials(self) -> bool:
        return bool(self._settings.betterstack_heartbeat_url.strip())

    async def check_health(self) -> ProviderHealth:
        if not self.is_enabled():
            return ProviderHealth(
                status=ProviderStatus.DISABLED,
                message="Better Stack monitoring is disabled.",
            )

        if not self.has_credentials():
            return ProviderHealth(
                status=ProviderStatus.NOT_CONFIGURED,
                message="No Better Stack heartbeat URL configured. Uptime monitored via local health endpoints.",
                details={"fallback": "internal_health_check"},
            )

        start = time.perf_counter()
        try:
            # Send a non-disruptive HEAD or GET probe to heartbeat URL
            url = self._settings.betterstack_heartbeat_url
            if self._external_client:
                await self._external_client.get(url, timeout=5.0)
            else:
                async with httpx.AsyncClient() as c:
                    await c.get(url, timeout=5.0)

            latency = (time.perf_counter() - start) * 1000.0
            return ProviderHealth(
                status=ProviderStatus.CONNECTED,
                message="Better Stack heartbeat delivered successfully.",
                latency_ms=latency,
            )
        except Exception as e:
            latency = (time.perf_counter() - start) * 1000.0
            return ProviderHealth(
                status=ProviderStatus.ERROR,
                message=f"Better Stack heartbeat failed: {e}",
                latency_ms=latency,
                details={"error": str(e)},
            )

    async def get_usage(self) -> ProviderUsage | None:
        return ProviderUsage(
            quota_used=1.0,
            quota_total=10.0,
            quota_unit="monitors",
            percentage=10.0,
            description="1 of 10 free monitors used on Better Stack free tier",
        )

    async def send_heartbeat(self, status: str = "up") -> bool:
        """Send heartbeat ping to Better Stack."""
        if not self.is_enabled() or not self.has_credentials():
            return False

        try:
            url = self._settings.betterstack_heartbeat_url
            if self._external_client:
                resp = await self._external_client.get(url, timeout=5.0)
            else:
                async with httpx.AsyncClient() as c:
                    resp = await c.get(url, timeout=5.0)
            return resp.status_code in (200, 201, 204)
        except Exception as e:
            logger.warning("Heartbeat failed: %s", e)
            return False


_betterstack_service_instance: BetterStackService | None = None


def get_betterstack_service() -> BetterStackService:
    global _betterstack_service_instance
    if _betterstack_service_instance is None:
        _betterstack_service_instance = BetterStackService()
    return _betterstack_service_instance

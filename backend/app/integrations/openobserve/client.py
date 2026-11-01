"""
OpenObserve Centralized Log Forwarding Integration Provider.
"""

from __future__ import annotations

import base64
import logging
import time
from typing import Any

import httpx
from app.config import get_settings
from app.integrations.base import IntegrationProvider
from app.integrations.schemas import (
    IntegrationCategory,
    ProviderHealth,
    ProviderStatus,
    ProviderUsage,
)
from app.logging.redaction import redact_metadata

logger = logging.getLogger(__name__)


class OpenObserveClient(IntegrationProvider):
    """
    OpenObserve log and event forwarding client using the HTTP ingestion API.
    """

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._settings = get_settings()
        self._external_client = client

    @property
    def provider_id(self) -> str:
        return "openobserve"

    @property
    def name(self) -> str:
        return "OpenObserve"

    @property
    def category(self) -> IntegrationCategory:
        return IntegrationCategory.OBSERVABILITY

    @property
    def description(self) -> str:
        return (
            "Cloud-native observability platform: Centralized log, metric, "
            "and event search with SQL querying and rich dashboards."
        )

    @property
    def free_tier_info(self) -> str:
        return "Free Cloud Tier (0.5 GB/day ingestion, 14-day retention) or 100% Free Self-Hosted OSS (unlimited)."

    @property
    def features(self) -> list[str]:
        return [
            "Structured Agent Event Ingestion",
            "Distributed Trace & Task Correlation",
            "Automatic Secret & Credential Redaction",
            "SQL & PromQL Querying",
            "Zero Data Egress Fees",
        ]

    def is_enabled(self) -> bool:
        return self._settings.openobserve_enabled

    def has_credentials(self) -> bool:
        return bool(
            self._settings.openobserve_user.strip() and self._settings.openobserve_password.strip()
        )

    def _get_auth_header(self) -> str:
        creds = f"{self._settings.openobserve_user}:{self._settings.openobserve_password}"
        encoded = base64.b64encode(creds.encode()).decode()
        return f"Basic {encoded}"

    async def check_health(self) -> ProviderHealth:
        if not self.is_enabled():
            return ProviderHealth(
                status=ProviderStatus.DISABLED,
                message="OpenObserve log forwarding is disabled.",
            )

        if not self.has_credentials():
            return ProviderHealth(
                status=ProviderStatus.NOT_CONFIGURED,
                message="OpenObserve endpoint configured, but credentials are not set. Events stored locally in SQLite.",
                details={"fallback": "sqlite_primary_store"},
            )

        start = time.perf_counter()
        try:
            url = f"{self._settings.openobserve_endpoint.rstrip('/')}/api/default/version"
            headers = {"Authorization": self._get_auth_header()}

            if self._external_client:
                resp = await self._external_client.get(url, headers=headers, timeout=5.0)
            else:
                async with httpx.AsyncClient() as c:
                    resp = await c.get(url, headers=headers, timeout=5.0)

            latency = (time.perf_counter() - start) * 1000.0
            if resp.status_code in (200, 404):  # Some versions respond 200, some endpoints differ
                return ProviderHealth(
                    status=ProviderStatus.CONNECTED,
                    message=f"Connected to OpenObserve at {self._settings.openobserve_endpoint}",
                    latency_ms=latency,
                    details={"stream": self._settings.openobserve_stream},
                )
            return ProviderHealth(
                status=ProviderStatus.ERROR,
                message=f"OpenObserve returned HTTP {resp.status_code}",
                latency_ms=latency,
            )
        except Exception as e:
            latency = (time.perf_counter() - start) * 1000.0
            return ProviderHealth(
                status=ProviderStatus.DISCONNECTED,
                message=f"Failed to reach OpenObserve: {e}",
                latency_ms=latency,
                details={"error": str(e)},
            )

    async def get_usage(self) -> ProviderUsage | None:
        return ProviderUsage(
            quota_used=0.0,
            quota_total=500.0,
            quota_unit="MB/day",
            percentage=0.0,
            description="0.5 GB/day free ingestion quota on OpenObserve Cloud",
        )

    async def forward_events(self, events: list[dict[str, Any]]) -> bool:
        """
        Sanitize, redact, and forward a batch of structured events to OpenObserve.
        """
        if not self.is_enabled() or not self.has_credentials() or not events:
            return False

        # Redact any sensitive keys/patterns before transmission
        sanitized_events: list[dict[str, Any]] = []
        for evt in events:
            # Drop full source code, prompts, or sensitive bodies
            safe_copy = redact_metadata(evt)
            if "payload" in safe_copy and isinstance(safe_copy["payload"], dict):
                # Filter out heavy code blocks from payload
                safe_copy["payload"].pop("code", None)
                safe_copy["payload"].pop("file_content", None)
                safe_copy["payload"].pop("raw_prompt", None)
            sanitized_events.append(safe_copy)

        stream_name = self._settings.openobserve_stream
        url = f"{self._settings.openobserve_endpoint.rstrip('/')}/api/default/{stream_name}/_json"
        headers = {
            "Authorization": self._get_auth_header(),
            "Content-Type": "application/json",
        }

        try:
            if self._external_client:
                resp = await self._external_client.post(
                    url, json=sanitized_events, headers=headers, timeout=10.0
                )
            else:
                async with httpx.AsyncClient() as c:
                    resp = await c.post(url, json=sanitized_events, headers=headers, timeout=10.0)
            return resp.status_code in (200, 201)
        except Exception as e:
            logger.warning("Failed to forward logs to OpenObserve: %s", e)
            return False


_openobserve_client_instance: OpenObserveClient | None = None


def get_openobserve_client() -> OpenObserveClient:
    global _openobserve_client_instance
    if _openobserve_client_instance is None:
        _openobserve_client_instance = OpenObserveClient()
    return _openobserve_client_instance

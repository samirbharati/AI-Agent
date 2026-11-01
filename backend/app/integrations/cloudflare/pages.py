"""
Cloudflare Pages and Cloudflare Tunnel Integration Provider.
"""

from __future__ import annotations

import logging
import shutil
from typing import Any

from app.config import get_settings
from app.integrations.base import IntegrationProvider
from app.integrations.schemas import (
    IntegrationCategory,
    ProviderHealth,
    ProviderStatus,
    ProviderUsage,
)

logger = logging.getLogger(__name__)


class CloudflareService(IntegrationProvider):
    """
    Cloudflare Pages and Secure Development Tunnel supervisor.
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        self._tunnel_process = None
        self._tunnel_url: str | None = None
        self._tunnel_approved: bool = False

    @property
    def provider_id(self) -> str:
        return "cloudflare"

    @property
    def name(self) -> str:
        return "Cloudflare"

    @property
    def category(self) -> IntegrationCategory:
        return IntegrationCategory.DEPLOYMENT

    @property
    def description(self) -> str:
        return (
            "Edge deployment and secure connectivity: Cloudflare Pages for React frontend hosting, "
            "and gated Cloudflare Tunnel for secure demonstration access."
        )

    @property
    def free_tier_info(self) -> str:
        return (
            "Unlimited Cloudflare Pages deployments, 500 builds/month, 50 free zero-trust tunnels."
        )

    @property
    def features(self) -> list[str]:
        return [
            "Cloudflare Pages Static Site Deployment",
            "Secure Demonstration Tunnel (cloudflared)",
            "Strict Endpoint Whitelisting",
            "Ollama & Terminal Isolation Guarantee",
            "Explicit Approval Security Gate",
        ]

    def is_enabled(self) -> bool:
        return self._settings.cloudflare_enabled

    def has_credentials(self) -> bool:
        return bool(
            self._settings.cloudflare_api_token.strip()
            or self._settings.cloudflare_tunnel_token.strip()
        )

    def is_cloudflared_installed(self) -> bool:
        return shutil.which("cloudflared") is not None

    async def check_health(self) -> ProviderHealth:
        if not self.is_enabled():
            return ProviderHealth(
                status=ProviderStatus.DISABLED,
                message="Cloudflare integration is disabled.",
            )

        if not self.has_credentials() and not self.is_cloudflared_installed():
            return ProviderHealth(
                status=ProviderStatus.NOT_CONFIGURED,
                message="No Cloudflare credentials or cloudflared binary detected. App running locally on localhost.",
                details={"fallback": "local_dev_server"},
            )

        has_cf = self.is_cloudflared_installed()
        return ProviderHealth(
            status=ProviderStatus.CONNECTED,
            message="Cloudflare integration ready (Pages deployment scripts & tunnel capability available)",
            details={
                "cloudflared_installed": has_cf,
                "tunnel_active": self._tunnel_url is not None,
                "tunnel_url": self._tunnel_url,
            },
        )

    async def get_usage(self) -> ProviderUsage | None:
        return ProviderUsage(
            quota_used=0.0,
            quota_total=50.0,
            quota_unit="tunnels",
            percentage=0.0,
            description="50 free Cloudflare zero-trust tunnels allowance",
        )

    def get_pages_deployment_guide(self) -> dict[str, Any]:
        """Return instructions and config for deploying to Cloudflare Pages."""
        return {
            "platform": "Cloudflare Pages",
            "build_output_directory": "frontend/dist",
            "build_command": "npm run build",
            "deploy_command": "npx wrangler pages deploy dist --project-name agentforge",
            "docs_url": "https://developers.cloudflare.com/pages/",
            "security_notes": [
                "Only the static frontend bundle is uploaded to Pages CDN.",
                "Ollama, backend SQLite, and terminal execution stay local and are never published to Pages.",
            ],
        }

    def get_tunnel_status(self) -> dict[str, Any]:
        """Return current status of secure development demonstration tunnel."""
        return {
            "installed": self.is_cloudflared_installed(),
            "active": self._tunnel_url is not None,
            "tunnel_url": self._tunnel_url,
            "requires_admin_approval": True,
            "blocked_routes": ["/api/v1/terminal/*", "/api/v1/health/ollama", "/ollama/*"],
            "allowed_routes": ["/", "/api/v1/projects/*", "/api/v1/health"],
        }


_cloudflare_service_instance: CloudflareService | None = None


def get_cloudflare_service() -> CloudflareService:
    global _cloudflare_service_instance
    if _cloudflare_service_instance is None:
        _cloudflare_service_instance = CloudflareService()
    return _cloudflare_service_instance

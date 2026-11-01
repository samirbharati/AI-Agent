"""
Integrations package initialization and automatic provider registration.
"""

from __future__ import annotations

from app.integrations.auth.rbac import get_auth_service
from app.integrations.backblaze.s3_client import get_backblaze_service
from app.integrations.betterstack.heartbeat import get_betterstack_service
from app.integrations.bugsink.reporter import get_bugsink_reporter
from app.integrations.cloudflare.pages import get_cloudflare_service
from app.integrations.github.actions import get_github_actions_service
from app.integrations.github.service import get_github_service
from app.integrations.manager import IntegrationManager, get_integration_manager
from app.integrations.openobserve.client import get_openobserve_client
from app.integrations.security.gitleaks_runner import get_gitleaks_runner
from app.integrations.security.semgrep_runner import get_semgrep_runner
from app.integrations.security.trivy_runner import get_trivy_runner


def initialize_integrations() -> IntegrationManager:
    """Register all default free developer service providers into the IntegrationManager."""
    mgr = get_integration_manager()

    mgr.register_provider(get_github_service())
    mgr.register_provider(get_github_actions_service())
    mgr.register_provider(get_semgrep_runner())
    mgr.register_provider(get_gitleaks_runner())
    mgr.register_provider(get_trivy_runner())
    mgr.register_provider(get_openobserve_client())
    mgr.register_provider(get_bugsink_reporter())
    mgr.register_provider(get_betterstack_service())
    mgr.register_provider(get_cloudflare_service())
    mgr.register_provider(get_backblaze_service())
    mgr.register_provider(get_auth_service())

    return mgr


# Auto-initialize when package imported
initialize_integrations()

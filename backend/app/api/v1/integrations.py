"""
FastAPI Router for Free Developer Services Integrations.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.integrations import get_integration_manager
from app.integrations.backblaze.s3_client import get_backblaze_service
from app.integrations.betterstack.heartbeat import get_betterstack_service
from app.integrations.bugsink.reporter import get_bugsink_reporter
from app.integrations.cloudflare.pages import get_cloudflare_service
from app.integrations.github.actions import get_github_actions_service
from app.integrations.github.schemas import (
    GitHubCreateBranchRequest,
    GitHubCreatePRRequest,
    GitHubMergePRRequest,
)
from app.integrations.github.service import get_github_service
from app.integrations.openobserve.client import get_openobserve_client
from app.integrations.schemas import (
    IntegrationCategory,
    IntegrationStatusResponse,
    IntegrationTestResult,
    IntegrationToggleRequest,
    ProviderUsage,
)
from app.integrations.security.aggregator import get_security_aggregator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/integrations", tags=["Integrations & Free Developer Services"])


# ─────────────────────────────────────────────────────────────────────────────
# 1. Integration Registry & Health Checks
# ─────────────────────────────────────────────────────────────────────────────


@router.get("/", response_model=list[IntegrationStatusResponse])
async def list_integrations(
    category: IntegrationCategory | None = None,
) -> list[IntegrationStatusResponse]:
    """List all registered developer service providers with live health and quota metrics."""
    mgr = get_integration_manager()
    return await mgr.get_all_statuses(category=category)


@router.get("/{provider_id}", response_model=IntegrationStatusResponse)
async def get_integration(provider_id: str) -> IntegrationStatusResponse:
    """Fetch status and health telemetry for a specific provider."""
    mgr = get_integration_manager()
    provider = mgr.get_provider(provider_id)
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Integration provider '{provider_id}' not found.",
        )
    return await provider.to_status_response()


@router.post("/{provider_id}/toggle")
async def toggle_integration(
    provider_id: str,
    payload: IntegrationToggleRequest,
) -> dict[str, Any]:
    """Enable or disable an integration provider at runtime."""
    mgr = get_integration_manager()
    success = mgr.set_provider_enabled(provider_id, payload.enabled)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Integration provider '{provider_id}' not found.",
        )
    return {"provider_id": provider_id, "enabled": payload.enabled}


@router.post("/{provider_id}/test", response_model=IntegrationTestResult)
async def test_integration(provider_id: str) -> IntegrationTestResult:
    """Run an on-demand connectivity test against a provider."""
    mgr = get_integration_manager()
    return await mgr.test_provider(provider_id)


@router.get("/{provider_id}/usage", response_model=ProviderUsage | None)
async def get_integration_usage(provider_id: str) -> ProviderUsage | None:
    """Fetch real-time quota and usage metrics from provider API."""
    mgr = get_integration_manager()
    provider = mgr.get_provider(provider_id)
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Integration provider '{provider_id}' not found.",
        )
    return await provider.get_usage()


# ─────────────────────────────────────────────────────────────────────────────
# 2. GitHub Operations (Repo, Branches, PRs, Commits, CI Checks)
# ─────────────────────────────────────────────────────────────────────────────


@router.get("/github/repos/{owner}/{repo}")
async def get_github_repo(owner: str, repo: str) -> dict[str, Any]:
    """Fetch GitHub repository metadata."""
    svc = get_github_service()
    res = await svc.get_repository(owner, repo)
    return res.model_dump()


@router.get("/github/repos/{owner}/{repo}/branches")
async def list_github_branches(owner: str, repo: str) -> list[dict[str, Any]]:
    """List branches in repository."""
    svc = get_github_service()
    branches = await svc.list_branches(owner, repo)
    return [b.model_dump() for b in branches]


@router.post("/github/repos/{owner}/{repo}/branches")
async def create_github_branch(
    owner: str, repo: str, payload: GitHubCreateBranchRequest
) -> dict[str, Any]:
    """Create a new branch for agent tasks."""
    svc = get_github_service()
    res = await svc.create_agent_branch(owner, repo, payload.branch_name, payload.base_branch)
    return res.model_dump()


@router.get("/github/repos/{owner}/{repo}/commits")
async def list_github_commits(
    owner: str, repo: str, sha: str = "main", limit: int = 30
) -> list[dict[str, Any]]:
    """List recent commits on a branch."""
    svc = get_github_service()
    commits = await svc.list_commits(owner, repo, sha, limit)
    return [c.model_dump() for c in commits]


@router.get("/github/repos/{owner}/{repo}/pulls")
async def list_github_pulls(owner: str, repo: str, state: str = "open") -> list[dict[str, Any]]:
    """List pull requests in repository."""
    svc = get_github_service()
    pulls = await svc.list_pull_requests(owner, repo, state)
    return [p.model_dump() for p in pulls]


@router.post("/github/repos/{owner}/{repo}/pulls")
async def create_github_pull(
    owner: str, repo: str, payload: GitHubCreatePRRequest
) -> dict[str, Any]:
    """Open a new Pull Request."""
    svc = get_github_service()
    pr = await svc.create_pull_request(
        owner, repo, payload.title, payload.head, payload.base, payload.body, payload.draft
    )
    return pr.model_dump()


@router.get("/github/repos/{owner}/{repo}/pulls/{number}")
async def get_github_pull(owner: str, repo: str, number: int) -> dict[str, Any]:
    """Get details of a pull request."""
    svc = get_github_service()
    pr = await svc.get_pull_request(owner, repo, number)
    return pr.model_dump()


@router.get("/github/repos/{owner}/{repo}/pulls/{number}/files")
async def get_github_pull_files(owner: str, repo: str, number: int) -> list[dict[str, Any]]:
    """Get changed files and diff stats for a pull request."""
    svc = get_github_service()
    files = await svc.get_changed_files(owner, repo, number)
    return [f.model_dump() for f in files]


@router.get("/github/repos/{owner}/{repo}/commits/{ref}/checks")
async def get_github_checks(owner: str, repo: str, ref: str) -> list[dict[str, Any]]:
    """Get CI check runs for a commit or branch ref."""
    svc = get_github_service()
    checks = await svc.get_pull_request_checks(owner, repo, ref)
    return [c.model_dump() for c in checks]


@router.put("/github/repos/{owner}/{repo}/pulls/{number}/merge")
async def merge_github_pull(
    owner: str, repo: str, number: int, payload: GitHubMergePRRequest
) -> dict[str, Any]:
    """Approve and merge a pull request."""
    svc = get_github_service()
    return await svc.merge_pull_request(
        owner, repo, number, payload.commit_title, payload.merge_method
    )


# ─────────────────────────────────────────────────────────────────────────────
# 3. GitHub Actions CI Operations
# ─────────────────────────────────────────────────────────────────────────────


@router.get("/github/actions/{owner}/{repo}/runs")
async def list_actions_runs(owner: str, repo: str, limit: int = 15) -> list[dict[str, Any]]:
    """Fetch GitHub Actions workflow runs."""
    actions = get_github_actions_service()
    runs = await actions.list_workflow_runs(owner, repo, limit)
    return [r.model_dump() for r in runs]


@router.get("/github/actions/{owner}/{repo}/runs/{run_id}/jobs")
async def list_actions_jobs(owner: str, repo: str, run_id: int) -> list[dict[str, Any]]:
    """Fetch individual jobs and step statuses for a workflow run."""
    actions = get_github_actions_service()
    jobs = await actions.get_workflow_jobs(owner, repo, run_id)
    return [j.model_dump() for j in jobs]


# ─────────────────────────────────────────────────────────────────────────────
# 4. Multi-Scanner Security Audit (Semgrep, Gitleaks, Trivy)
# ─────────────────────────────────────────────────────────────────────────────


@router.post("/security/audit/{project_id}")
async def run_security_audit(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Execute Semgrep, Gitleaks, and Trivy scans on the project workspace."""
    aggregator = get_security_aggregator()
    return await aggregator.run_full_security_audit(project_id, db=db)


# ─────────────────────────────────────────────────────────────────────────────
# 5. OpenObserve Log Ingestion
# ─────────────────────────────────────────────────────────────────────────────


@router.post("/openobserve/forward")
async def forward_to_openobserve(
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    """Forward a batch of sanitized structured events to OpenObserve."""
    client = get_openobserve_client()
    success = await client.forward_events(events)
    return {"success": success, "count": len(events)}


# ─────────────────────────────────────────────────────────────────────────────
# 6. Bugsink Error Reporting
# ─────────────────────────────────────────────────────────────────────────────


@router.post("/bugsink/report")
async def report_to_bugsink(
    error_data: dict[str, Any],
) -> dict[str, Any]:
    """Ingest frontend or client error and forward to Bugsink."""
    reporter = get_bugsink_reporter()
    success = await reporter.capture_frontend_error(error_data)
    return {"success": success}


# ─────────────────────────────────────────────────────────────────────────────
# 7. Better Stack Uptime Monitoring
# ─────────────────────────────────────────────────────────────────────────────


@router.post("/betterstack/heartbeat")
async def trigger_betterstack_heartbeat() -> dict[str, Any]:
    """Send immediate uptime heartbeat ping to Better Stack."""
    svc = get_betterstack_service()
    success = await svc.send_heartbeat()
    return {"success": success}


# ─────────────────────────────────────────────────────────────────────────────
# 8. Cloudflare Deployment & Tunnel
# ─────────────────────────────────────────────────────────────────────────────


@router.get("/cloudflare/status")
async def get_cloudflare_status() -> dict[str, Any]:
    """Get Cloudflare Pages deployment info and Tunnel supervisor status."""
    svc = get_cloudflare_service()
    return {
        "pages": svc.get_pages_deployment_guide(),
        "tunnel": svc.get_tunnel_status(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 9. Backblaze B2 Artifact Storage
# ─────────────────────────────────────────────────────────────────────────────


@router.get("/backblaze/artifacts")
async def list_backblaze_artifacts(
    project_id: str | None = None,
) -> list[dict[str, Any]]:
    """List archived artifacts stored on Backblaze B2."""
    svc = get_backblaze_service()
    return await svc.list_artifacts(project_id)


@router.post("/backblaze/artifacts/{project_id}")
async def upload_backblaze_artifact(
    project_id: str,
    filename: str,
    content: str,
) -> dict[str, Any]:
    """Archive a project artifact to Backblaze B2."""
    svc = get_backblaze_service()
    return await svc.upload_artifact(project_id, filename, content)

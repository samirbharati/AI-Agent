"""
GitHub Actions CI/CD Provider Integration Service.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from app.config import get_settings
from app.integrations.base import IntegrationProvider
from app.integrations.github.client import GitHubClient
from app.integrations.schemas import (
    IntegrationCategory,
    ProviderHealth,
    ProviderStatus,
    ProviderUsage,
)
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class WorkflowRunSummary(BaseModel):
    id: int
    name: str
    status: str
    conclusion: str | None = None
    workflow_id: int
    event: str
    head_branch: str
    head_sha: str
    html_url: str
    created_at: str
    updated_at: str
    run_attempt: int = 1
    actor: str = "system"


class WorkflowJobSummary(BaseModel):
    id: int
    run_id: int
    name: str
    status: str
    conclusion: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    html_url: str | None = None
    steps: list[dict[str, Any]] = []


class GitHubActionsService(IntegrationProvider):
    """
    Provider exposing GitHub Actions workflow runs, status, and job logs
    within AgentForge dashboards.
    """

    def __init__(self, client: GitHubClient | None = None) -> None:
        self._settings = get_settings()
        self._client = client

    @property
    def client(self) -> GitHubClient:
        if self._client is None:
            self._client = GitHubClient(token=self._settings.github_token)
        return self._client

    @property
    def provider_id(self) -> str:
        return "github_actions"

    @property
    def name(self) -> str:
        return "GitHub Actions"

    @property
    def category(self) -> IntegrationCategory:
        return IntegrationCategory.CI_CD

    @property
    def description(self) -> str:
        return (
            "Continuous Integration & Deployment: Automated Pytest runs, Ruff linting, "
            "Vite TypeScript builds, Docker verification, and security scans."
        )

    @property
    def free_tier_info(self) -> str:
        return "2,000 free CI minutes/month for standard GitHub Linux runners, unlimited for public repositories."

    @property
    def features(self) -> list[str]:
        return [
            "Workflow Run Inspection",
            "Job Step Logs",
            "CI Status Sync",
            "Manual Workflow Dispatch",
            "Failure Diagnosis",
        ]

    def is_enabled(self) -> bool:
        return self._settings.github_enabled

    def has_credentials(self) -> bool:
        return bool(self._settings.github_token.strip())

    async def check_health(self) -> ProviderHealth:
        if not self.is_enabled():
            return ProviderHealth(
                status=ProviderStatus.DISABLED,
                message="GitHub Actions integration disabled.",
            )
        if not self.has_credentials():
            return ProviderHealth(
                status=ProviderStatus.NOT_CONFIGURED,
                message="No GitHub token provided. Running local verification runner.",
                details={"fallback": "local_qa_runner"},
            )

        start = time.perf_counter()
        try:
            # Probe rate limit to verify token
            rl = await self.client.get_rate_limit()
            latency = (time.perf_counter() - start) * 1000.0
            return ProviderHealth(
                status=ProviderStatus.CONNECTED,
                message=f"Actions API ready ({rl.remaining} calls remaining)",
                latency_ms=latency,
            )
        except Exception as e:
            latency = (time.perf_counter() - start) * 1000.0
            return ProviderHealth(
                status=ProviderStatus.ERROR,
                message=f"GitHub Actions connectivity error: {e}",
                latency_ms=latency,
                details={"error": str(e)},
            )

    async def get_usage(self) -> ProviderUsage | None:
        """Estimate CI usage from workflow minutes if owner is configured."""
        return ProviderUsage(
            quota_used=0.0,
            quota_total=2000.0,
            quota_unit="minutes/month",
            percentage=0.0,
            description="2,000 minutes/month free allowance for standard Linux runners",
        )

    async def list_workflow_runs(
        self, owner: str, repo: str, limit: int = 15
    ) -> list[WorkflowRunSummary]:
        """Fetch recent workflow runs for the repository."""
        data = await self.client._request(
            "GET", f"/repos/{owner}/{repo}/actions/runs", params={"per_page": limit}
        )
        runs: list[WorkflowRunSummary] = []
        for r in data.get("workflow_runs", []):
            runs.append(
                WorkflowRunSummary(
                    id=r["id"],
                    name=r.get("name", "CI"),
                    status=r.get("status", "completed"),
                    conclusion=r.get("conclusion"),
                    workflow_id=r.get("workflow_id", 0),
                    event=r.get("event", "push"),
                    head_branch=r.get("head_branch", "main"),
                    head_sha=r.get("head_sha", "")[:8],
                    html_url=r.get("html_url", ""),
                    created_at=r.get("created_at", ""),
                    updated_at=r.get("updated_at", ""),
                    run_attempt=r.get("run_attempt", 1),
                    actor=r.get("actor", {}).get("login", "system"),
                )
            )
        return runs

    async def get_workflow_jobs(
        self, owner: str, repo: str, run_id: int
    ) -> list[WorkflowJobSummary]:
        """Fetch all individual jobs and step statuses for a run."""
        data = await self.client._request(
            "GET", f"/repos/{owner}/{repo}/actions/runs/{run_id}/jobs"
        )
        jobs: list[WorkflowJobSummary] = []
        for j in data.get("jobs", []):
            jobs.append(
                WorkflowJobSummary(
                    id=j["id"],
                    run_id=j["run_id"],
                    name=j["name"],
                    status=j["status"],
                    conclusion=j.get("conclusion"),
                    started_at=j.get("started_at"),
                    completed_at=j.get("completed_at"),
                    html_url=j.get("html_url"),
                    steps=[
                        {
                            "name": s["name"],
                            "status": s["status"],
                            "conclusion": s.get("conclusion"),
                            "number": s["number"],
                        }
                        for s in j.get("steps", [])
                    ],
                )
            )
        return jobs

    async def dispatch_workflow(
        self,
        owner: str,
        repo: str,
        workflow_id_or_file: str,
        ref: str = "main",
        inputs: dict[str, Any] | None = None,
    ) -> bool:
        """Trigger a manual workflow dispatch event."""
        payload: dict[str, Any] = {"ref": ref}
        if inputs:
            payload["inputs"] = inputs
        await self.client._request(
            "POST",
            f"/repos/{owner}/{repo}/actions/workflows/{workflow_id_or_file}/dispatches",
            json_data=payload,
        )
        return True


_github_actions_instance: GitHubActionsService | None = None


def get_github_actions_service() -> GitHubActionsService:
    global _github_actions_instance
    if _github_actions_instance is None:
        _github_actions_instance = GitHubActionsService()
    return _github_actions_instance

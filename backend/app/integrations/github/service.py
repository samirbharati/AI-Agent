"""
GitHub Provider Integration Service.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from app.config import get_settings
from app.integrations.base import IntegrationProvider
from app.integrations.github.client import GitHubClient
from app.integrations.github.schemas import (
    GitHubBranch,
    GitHubChangedFile,
    GitHubCheckRun,
    GitHubCommit,
    GitHubPullRequest,
    GitHubRepoSummary,
)
from app.integrations.schemas import (
    IntegrationCategory,
    ProviderHealth,
    ProviderStatus,
    ProviderUsage,
)

logger = logging.getLogger(__name__)


class GitHubService(IntegrationProvider):
    """
    AgentForge GitHub Provider coordinating remote repository operations,
    agent branch creation, PR automation, and CI monitoring.
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
        return "github"

    @property
    def name(self) -> str:
        return "GitHub"

    @property
    def category(self) -> IntegrationCategory:
        return IntegrationCategory.VCS

    @property
    def description(self) -> str:
        return (
            "Repository management, automated agent task branches, commit history, "
            "pull request lifecycle, changed-file inspection, and CI status checks."
        )

    @property
    def free_tier_info(self) -> str:
        return (
            "Free for Public & Private Repositories: Unlimited public/private repos, "
            "2,000 Actions CI minutes/month, 5,000 REST API requests/hour."
        )

    @property
    def features(self) -> list[str]:
        return [
            "Repository Connection",
            "Agent Branch Creation",
            "Commit History",
            "Pull Request Automation",
            "Diff & File Inspection",
            "CI Check Status",
            "Merge Approval Workflow",
        ]

    def is_enabled(self) -> bool:
        return self._settings.github_enabled

    def has_credentials(self) -> bool:
        return bool(self._settings.github_token.strip())

    async def check_health(self) -> ProviderHealth:
        """Verify connectivity and token permissions with GitHub API."""
        if not self.is_enabled():
            return ProviderHealth(
                status=ProviderStatus.DISABLED,
                message="GitHub integration is disabled in configuration.",
            )

        if not self.has_credentials():
            return ProviderHealth(
                status=ProviderStatus.NOT_CONFIGURED,
                message="No GitHub Personal Access Token configured. Running in local git mode.",
                details={"fallback_mode": "local_git"},
            )

        start = time.perf_counter()
        try:
            user_data = await self.client.get_current_user()
            rate_data = await self.client.get_rate_limit()
            latency = (time.perf_counter() - start) * 1000.0

            return ProviderHealth(
                status=ProviderStatus.CONNECTED,
                message=f"Connected as @{user_data.get('login')} ({rate_data.remaining}/{rate_data.limit} API calls remaining)",
                latency_ms=latency,
                details={
                    "user": user_data.get("login"),
                    "user_type": user_data.get("type"),
                    "rate_limit_remaining": rate_data.remaining,
                    "rate_limit_total": rate_data.limit,
                },
            )
        except Exception as e:
            latency = (time.perf_counter() - start) * 1000.0
            logger.error("GitHub health check failed: %s", e)
            return ProviderHealth(
                status=ProviderStatus.DISCONNECTED,
                message=f"Failed to connect to GitHub: {e}",
                latency_ms=latency,
                details={"error": str(e)},
            )

    async def get_usage(self) -> ProviderUsage | None:
        """Fetch current GitHub REST API rate limit quota usage."""
        if not self.has_credentials():
            return None
        try:
            rl = await self.client.get_rate_limit()
            used_pct = ((rl.limit - rl.remaining) / rl.limit * 100.0) if rl.limit > 0 else 0.0
            return ProviderUsage(
                quota_used=float(rl.limit - rl.remaining),
                quota_total=float(rl.limit),
                quota_unit="requests/hour",
                percentage=round(used_pct, 1),
                description=f"{rl.remaining} of {rl.limit} API requests remaining",
            )
        except Exception:
            return None

    # Domain methods for AgentForge workflows
    async def get_repository(self, owner: str, repo: str) -> GitHubRepoSummary:
        return await self.client.get_repo(owner, repo)

    async def list_branches(self, owner: str, repo: str) -> list[GitHubBranch]:
        return await self.client.list_branches(owner, repo)

    async def create_agent_branch(
        self, owner: str, repo: str, branch_name: str, base_branch: str = "main"
    ) -> GitHubBranch:
        """Create a dedicated Git branch for an AI agent task."""
        return await self.client.create_branch(owner, repo, branch_name, base_branch)

    async def list_commits(
        self, owner: str, repo: str, sha: str = "main", limit: int = 30
    ) -> list[GitHubCommit]:
        return await self.client.list_commits(owner, repo, sha, limit)

    async def create_pull_request(
        self,
        owner: str,
        repo: str,
        title: str,
        head: str,
        base: str = "main",
        body: str = "",
        draft: bool = False,
    ) -> GitHubPullRequest:
        return await self.client.create_pull_request(owner, repo, title, head, base, body, draft)

    async def get_pull_request(self, owner: str, repo: str, pull_number: int) -> GitHubPullRequest:
        return await self.client.get_pull_request(owner, repo, pull_number)

    async def list_pull_requests(
        self, owner: str, repo: str, state: str = "open"
    ) -> list[GitHubPullRequest]:
        return await self.client.list_pull_requests(owner, repo, state)

    async def get_changed_files(
        self, owner: str, repo: str, pull_number: int
    ) -> list[GitHubChangedFile]:
        return await self.client.get_changed_files(owner, repo, pull_number)

    async def get_pull_request_checks(
        self, owner: str, repo: str, ref: str
    ) -> list[GitHubCheckRun]:
        return await self.client.get_pull_request_checks(owner, repo, ref)

    async def merge_pull_request(
        self,
        owner: str,
        repo: str,
        pull_number: int,
        commit_title: str | None = None,
        merge_method: str = "merge",
    ) -> dict[str, Any]:
        return await self.client.merge_pull_request(
            owner, repo, pull_number, commit_title, merge_method
        )


_github_service_instance: GitHubService | None = None


def get_github_service() -> GitHubService:
    global _github_service_instance
    if _github_service_instance is None:
        _github_service_instance = GitHubService()
    return _github_service_instance

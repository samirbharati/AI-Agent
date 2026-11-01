"""
Async HTTP Client for GitHub REST API v3.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
from app.integrations.github.schemas import (
    GitHubBranch,
    GitHubChangedFile,
    GitHubCheckRun,
    GitHubCommit,
    GitHubPullRequest,
    GitHubRateLimit,
    GitHubRepoSummary,
)

logger = logging.getLogger(__name__)

GITHUB_API_BASE = "https://api.github.com"


class GitHubClient:
    """Async client interacting directly with the GitHub REST API."""

    def __init__(
        self,
        token: str = "",
        base_url: str = GITHUB_API_BASE,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.token = token.strip()
        self.base_url = base_url.rstrip("/")
        self._external_client = client

    def _get_headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "AgentForge-DevPlatform/0.1.0",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
    ) -> Any:
        url = f"{self.base_url}/{path.lstrip('/')}"
        headers = self._get_headers()

        if self._external_client:
            resp = await self._external_client.request(
                method, url, headers=headers, params=params, json=json_data, timeout=30.0
            )
        else:
            async with httpx.AsyncClient() as c:
                resp = await c.request(
                    method, url, headers=headers, params=params, json=json_data, timeout=30.0
                )

        if resp.status_code >= 400:
            error_data = resp.text
            try:
                error_data = resp.json().get("message", resp.text)
            except Exception:
                error_data = resp.text
            logger.warning(
                "GitHub API %s %s returned %d: %s",
                method,
                path,
                resp.status_code,
                error_data,
            )
            resp.raise_for_status()

        if resp.status_code == 204:
            return None
        return resp.json()

    async def get_current_user(self) -> dict[str, Any]:
        """Fetch authenticated user profile."""
        return await self._request("GET", "/user")

    async def get_rate_limit(self) -> GitHubRateLimit:
        """Fetch GitHub API rate limit status."""
        data = await self._request("GET", "/rate_limit")
        core = data.get("resources", {}).get("core", {})
        return GitHubRateLimit(
            limit=core.get("limit", 5000),
            remaining=core.get("remaining", 5000),
            reset_timestamp=core.get("reset", 0),
            used=core.get("used", 0),
            resource="core",
        )

    async def get_repo(self, owner: str, repo: str) -> GitHubRepoSummary:
        """Fetch repository summary metadata."""
        data = await self._request("GET", f"/repos/{owner}/{repo}")
        return GitHubRepoSummary(
            name=data["name"],
            full_name=data["full_name"],
            owner=data["owner"]["login"],
            description=data.get("description"),
            private=data.get("private", False),
            default_branch=data.get("default_branch", "main"),
            html_url=data["html_url"],
            stars_count=data.get("stargazers_count", 0),
            forks_count=data.get("forks_count", 0),
            open_issues_count=data.get("open_issues_count", 0),
        )

    async def list_branches(self, owner: str, repo: str) -> list[GitHubBranch]:
        """List branches in repository."""
        data = await self._request("GET", f"/repos/{owner}/{repo}/branches")
        return [
            GitHubBranch(
                name=b["name"],
                commit_sha=b["commit"]["sha"],
                protected=b.get("protected", False),
            )
            for b in data
        ]

    async def create_branch(
        self, owner: str, repo: str, branch_name: str, base_branch: str = "main"
    ) -> GitHubBranch:
        """Create a new branch from a base branch ref."""
        # 1. Get base branch commit SHA
        ref_data = await self._request("GET", f"/repos/{owner}/{repo}/git/ref/heads/{base_branch}")
        base_sha = ref_data["object"]["sha"]

        # 2. Create the new reference
        payload = {"ref": f"refs/heads/{branch_name}", "sha": base_sha}
        created = await self._request("POST", f"/repos/{owner}/{repo}/git/refs", json_data=payload)
        return GitHubBranch(name=branch_name, commit_sha=created["object"]["sha"])

    async def list_commits(
        self, owner: str, repo: str, sha: str = "main", limit: int = 30
    ) -> list[GitHubCommit]:
        """Fetch recent commit history for branch or ref."""
        data = await self._request(
            "GET", f"/repos/{owner}/{repo}/commits", params={"sha": sha, "per_page": limit}
        )
        commits: list[GitHubCommit] = []
        for c in data:
            commit_data = c.get("commit", {})
            author = commit_data.get("author", {})
            commits.append(
                GitHubCommit(
                    sha=c["sha"],
                    message=commit_data.get("message", ""),
                    author_name=author.get("name", "Unknown"),
                    author_email=author.get("email"),
                    date=author.get("date", ""),
                    html_url=c.get("html_url"),
                )
            )
        return commits

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
        """Create a new Pull Request."""
        payload = {
            "title": title,
            "head": head,
            "base": base,
            "body": body,
            "draft": draft,
        }
        data = await self._request("POST", f"/repos/{owner}/{repo}/pulls", json_data=payload)
        return self._parse_pr(data)

    async def get_pull_request(self, owner: str, repo: str, pull_number: int) -> GitHubPullRequest:
        """Fetch details of a single PR."""
        data = await self._request("GET", f"/repos/{owner}/{repo}/pulls/{pull_number}")
        return self._parse_pr(data)

    async def list_pull_requests(
        self, owner: str, repo: str, state: str = "open"
    ) -> list[GitHubPullRequest]:
        """List pull requests in repository."""
        data = await self._request(
            "GET", f"/repos/{owner}/{repo}/pulls", params={"state": state, "per_page": 50}
        )
        return [self._parse_pr(p) for p in data]

    async def get_changed_files(
        self, owner: str, repo: str, pull_number: int
    ) -> list[GitHubChangedFile]:
        """List files changed in a PR with diff stats."""
        data = await self._request("GET", f"/repos/{owner}/{repo}/pulls/{pull_number}/files")
        return [
            GitHubChangedFile(
                filename=f["filename"],
                status=f["status"],
                additions=f.get("additions", 0),
                deletions=f.get("deletions", 0),
                changes=f.get("changes", 0),
                raw_url=f.get("raw_url"),
                patch=f.get("patch"),
            )
            for f in data
        ]

    async def get_pull_request_checks(
        self, owner: str, repo: str, ref: str
    ) -> list[GitHubCheckRun]:
        """Fetch CI check runs and commit statuses for ref/branch."""
        data = await self._request("GET", f"/repos/{owner}/{repo}/commits/{ref}/check-runs")
        check_runs = data.get("check_runs", [])
        return [
            GitHubCheckRun(
                id=c["id"],
                name=c["name"],
                status=c["status"],
                conclusion=c.get("conclusion"),
                html_url=c.get("html_url"),
                started_at=c.get("started_at"),
                completed_at=c.get("completed_at"),
            )
            for c in check_runs
        ]

    async def merge_pull_request(
        self,
        owner: str,
        repo: str,
        pull_number: int,
        commit_title: str | None = None,
        merge_method: str = "merge",
    ) -> dict[str, Any]:
        """Merge a Pull Request."""
        payload: dict[str, Any] = {"merge_method": merge_method}
        if commit_title:
            payload["commit_title"] = commit_title
        return await self._request(
            "PUT", f"/repos/{owner}/{repo}/pulls/{pull_number}/merge", json_data=payload
        )

    def _parse_pr(self, data: dict[str, Any]) -> GitHubPullRequest:
        return GitHubPullRequest(
            number=data["number"],
            title=data["title"],
            body=data.get("body"),
            state=data.get("state", "open"),
            html_url=data.get("html_url", ""),
            head_branch=data["head"]["ref"],
            base_branch=data["base"]["ref"],
            author=data.get("user", {}).get("login", "unknown"),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at"),
            merged=data.get("merged", False),
            mergeable=data.get("mergeable"),
            draft=data.get("draft", False),
        )

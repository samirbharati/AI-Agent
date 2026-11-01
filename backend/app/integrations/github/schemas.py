"""
Pydantic schemas for GitHub integration.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class GitHubRepoSummary(BaseModel):
    name: str
    full_name: str
    owner: str
    description: str | None = None
    private: bool = False
    default_branch: str = "main"
    html_url: str
    stars_count: int = 0
    forks_count: int = 0
    open_issues_count: int = 0


class GitHubBranch(BaseModel):
    name: str
    commit_sha: str
    protected: bool = False


class GitHubCommit(BaseModel):
    sha: str
    message: str
    author_name: str
    author_email: str | None = None
    date: datetime | str
    html_url: str | None = None


class GitHubPullRequest(BaseModel):
    number: int
    title: str
    body: str | None = None
    state: str = "open"
    html_url: str
    head_branch: str
    base_branch: str
    author: str
    created_at: datetime | str
    updated_at: datetime | str | None = None
    merged: bool = False
    mergeable: bool | None = None
    draft: bool = False


class GitHubChangedFile(BaseModel):
    filename: str
    status: str
    additions: int = 0
    deletions: int = 0
    changes: int = 0
    raw_url: str | None = None
    patch: str | None = None


class GitHubCheckRun(BaseModel):
    id: int
    name: str
    status: str
    conclusion: str | None = None
    html_url: str | None = None
    started_at: datetime | str | None = None
    completed_at: datetime | str | None = None


class GitHubCreateBranchRequest(BaseModel):
    branch_name: str
    base_branch: str = "main"


class GitHubCreatePRRequest(BaseModel):
    title: str
    head: str
    base: str = "main"
    body: str = ""
    draft: bool = False


class GitHubMergePRRequest(BaseModel):
    commit_title: str | None = None
    merge_method: str = Field(default="merge", pattern="^(merge|squash|rebase)$")


class GitHubRateLimit(BaseModel):
    limit: int = 5000
    remaining: int = 5000
    reset_timestamp: int = 0
    used: int = 0
    resource: str = "core"

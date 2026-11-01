"""
Workspace and Filesystem Management Service.

Handles isolated project directories, safe path resolution, file read/write
operations, path traversal protection, and per-project Git repositories.

Security guarantees:
  - All file operations are strictly confined within the project directory:
    ``workspace_base_dir / project_id``.
  - Any path containing ``..``, absolute paths, or resolving outside the
    project root raises ``PathTraversalError``.
  - AgentForge backend code and configuration can never be overwritten.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.config import get_settings

logger = logging.getLogger(__name__)


class PathTraversalError(ValueError):
    """Raised when an operation attempts to access files outside the project workspace."""


@dataclass
class FileInfo:
    """Metadata for a file within a project workspace."""

    path: str  # Relative path within project workspace
    size_bytes: int
    modified_at: str
    is_directory: bool = False


class WorkspaceService:
    """
    Manages local workspace directories for generated projects.

    Each project receives an isolated directory:
      ``<workspace_base_dir>/<project_id>/``
    """

    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or get_settings().workspace_path
        self.base_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Path safety & resolution
    # ------------------------------------------------------------------

    def get_project_dir(self, project_id: str) -> Path:
        """
        Get the root directory for a project, creating it if needed.

        Args:
            project_id: Project UUID string.

        Returns:
            Absolute Path to project root directory.
        """
        if not project_id or "/" in project_id or "\\" in project_id or ".." in project_id:
            raise PathTraversalError(f"Invalid project_id: {project_id!r}")

        project_dir = (self.base_dir / project_id).resolve()
        project_dir.mkdir(parents=True, exist_ok=True)
        return project_dir

    def resolve_safe_path(self, project_id: str, relative_path: str) -> Path:
        """
        Resolve a relative path inside a project workspace.

        Strictly enforces that the target is contained within the project directory.

        Args:
            project_id: Project identifier.
            relative_path: Path relative to the project root.

        Returns:
            Resolved absolute Path.

        Raises:
            PathTraversalError: If the path attempts to escape the project directory.
        """
        project_dir = self.get_project_dir(project_id)
        stripped = relative_path.strip()

        # Reject or resolve absolute paths
        if Path(stripped).is_absolute() or stripped.startswith(("/", "\\")):
            target = Path(stripped).resolve()
        else:
            target = (project_dir / stripped).resolve()

        try:
            # Python 3.9+ is_relative_to
            is_sub = target.is_relative_to(project_dir)
        except AttributeError:
            is_sub = str(target).startswith(str(project_dir))

        if not is_sub:
            logger.warning(
                "Security violation: path traversal attempt in project %s: %s -> %s",
                project_id,
                relative_path,
                target,
            )
            raise PathTraversalError(
                f"Access denied: path '{relative_path}' resolves outside project workspace."
            )

        return target

    # ------------------------------------------------------------------
    # File operations
    # ------------------------------------------------------------------

    def write_file(self, project_id: str, relative_path: str, content: str) -> FileInfo:
        """
        Write a text file into the project workspace.

        Parent directories are created automatically.
        """
        target = self.resolve_safe_path(project_id, relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)

        target.write_text(content, encoding="utf-8")
        stat = target.stat()

        rel_str = str(target.relative_to(self.get_project_dir(project_id))).replace("\\", "/")
        return FileInfo(
            path=rel_str,
            size_bytes=stat.st_size,
            modified_at=datetime.fromtimestamp(stat.st_mtime, tz=UTC).isoformat(),
            is_directory=False,
        )

    def read_file(self, project_id: str, relative_path: str) -> str:
        """
        Read the contents of a text file from the project workspace.

        Raises:
            FileNotFoundError: If the file does not exist.
        """
        target = self.resolve_safe_path(project_id, relative_path)
        if not target.exists() or not target.is_file():
            raise FileNotFoundError(f"File '{relative_path}' not found in project '{project_id}'.")
        return target.read_text(encoding="utf-8")

    def file_exists(self, project_id: str, relative_path: str) -> bool:
        """Check if a file exists in the project workspace."""
        try:
            target = self.resolve_safe_path(project_id, relative_path)
            return target.exists() and target.is_file()
        except PathTraversalError:
            return False

    def delete_file(self, project_id: str, relative_path: str) -> bool:
        """Delete a file from the project workspace."""
        target = self.resolve_safe_path(project_id, relative_path)
        if target.exists() and target.is_file():
            target.unlink()
            return True
        return False

    def list_files(
        self,
        project_id: str,
        subpath: str = "",
        exclude_patterns: tuple[str, ...] = (
            ".git",
            "__pycache__",
            ".pytest_cache",
            ".ruff_cache",
            "node_modules",
            ".venv",
            "venv",
        ),
    ) -> list[FileInfo]:
        """
        Recursively list files in the project workspace.

        Ignores version control and dependency directories.
        """
        target_dir = self.resolve_safe_path(project_id, subpath)
        if not target_dir.exists() or not target_dir.is_dir():
            return []

        project_dir = self.get_project_dir(project_id)
        results: list[FileInfo] = []

        for root, dirs, files in os.walk(target_dir):
            # Prune excluded directories in-place
            dirs[:] = [d for d in dirs if d not in exclude_patterns]

            for fname in files:
                fpath = Path(root) / fname
                try:
                    rel = str(fpath.relative_to(project_dir)).replace("\\", "/")
                    stat = fpath.stat()
                    results.append(
                        FileInfo(
                            path=rel,
                            size_bytes=stat.st_size,
                            modified_at=datetime.fromtimestamp(stat.st_mtime, tz=UTC).isoformat(),
                            is_directory=False,
                        )
                    )
                except (OSError, ValueError):
                    continue

        results.sort(key=lambda f: f.path)
        return results

    def clear_project_workspace(self, project_id: str) -> None:
        """Completely clean the project workspace directory."""
        project_dir = self.get_project_dir(project_id)
        if project_dir.exists():
            shutil.rmtree(project_dir, ignore_errors=True)
            project_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Git version control
    # ------------------------------------------------------------------

    def init_git_repo(self, project_id: str) -> bool:
        """
        Initialize a Git repository for the project if one does not exist.

        Configures local committer identity so commits work cleanly without
        relying on global user configuration.
        """
        project_dir = self.get_project_dir(project_id)
        git_dir = project_dir / ".git"

        if git_dir.exists():
            return True

        try:
            # 1. git init
            subprocess.run(
                ["git", "init", "-b", "main"],
                cwd=project_dir,
                capture_output=True,
                check=True,
                text=True,
            )

            # 2. Local author config
            subprocess.run(
                ["git", "config", "user.name", "AgentForge Developer"],
                cwd=project_dir,
                capture_output=True,
                check=True,
                text=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "developer@agentforge.local"],
                cwd=project_dir,
                capture_output=True,
                check=True,
                text=True,
            )

            # 3. Initial .gitignore
            gitignore = project_dir / ".gitignore"
            if not gitignore.exists():
                gitignore.write_text(
                    "__pycache__/\n*.pyc\n.pytest_cache/\nnode_modules/\n.env\n",
                    encoding="utf-8",
                )
                subprocess.run(
                    ["git", "add", ".gitignore"],
                    cwd=project_dir,
                    capture_output=True,
                    check=True,
                    text=True,
                )
                subprocess.run(
                    ["git", "commit", "-m", "chore: initial project repository"],
                    cwd=project_dir,
                    capture_output=True,
                    check=True,
                    text=True,
                )

            logger.info("Initialized Git repository for project %s", project_id)
            return True

        except (subprocess.SubprocessError, FileNotFoundError) as exc:
            logger.warning("Could not initialize Git repo for project %s: %s", project_id, exc)
            return False

    def create_or_checkout_branch(self, project_id: str, branch_name: str) -> bool:
        """Create or switch to a dedicated Git branch for a task or feature."""
        project_dir = self.get_project_dir(project_id)
        if not (project_dir / ".git").exists():
            self.init_git_repo(project_id)

        try:
            # Check if branch already exists
            res = subprocess.run(
                ["git", "checkout", branch_name],
                cwd=project_dir,
                capture_output=True,
                text=True,
            )
            if res.returncode == 0:
                return True

            # Otherwise create it
            subprocess.run(
                ["git", "checkout", "-b", branch_name],
                cwd=project_dir,
                capture_output=True,
                check=True,
                text=True,
            )
            return True
        except subprocess.SubprocessError as exc:
            logger.warning(
                "Failed to checkout branch %s in project %s: %s", branch_name, project_id, exc
            )
            return False

    def commit_all(self, project_id: str, commit_message: str) -> str | None:
        """
        Stage all changes and commit.

        Returns the short commit hash on success, or None if nothing changed / error.
        """
        project_dir = self.get_project_dir(project_id)
        if not (project_dir / ".git").exists():
            self.init_git_repo(project_id)

        try:
            subprocess.run(
                ["git", "add", "-A"],
                cwd=project_dir,
                capture_output=True,
                check=True,
                text=True,
            )
            commit_res = subprocess.run(
                ["git", "commit", "-m", commit_message],
                cwd=project_dir,
                capture_output=True,
                text=True,
            )
            if commit_res.returncode != 0:
                # Likely nothing to commit
                return None

            hash_res = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=project_dir,
                capture_output=True,
                check=True,
                text=True,
            )
            return hash_res.stdout.strip()

        except subprocess.SubprocessError as exc:
            logger.warning("Failed to commit in project %s: %s", project_id, exc)
            return None

    def get_git_status(self, project_id: str) -> dict[str, Any]:
        """Get the current Git branch and working directory status."""
        project_dir = self.get_project_dir(project_id)
        if not (project_dir / ".git").exists():
            return {"initialized": False, "branch": None, "modified": [], "untracked": []}

        try:
            branch_res = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=project_dir,
                capture_output=True,
                check=True,
                text=True,
            )
            status_res = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=project_dir,
                capture_output=True,
                check=True,
                text=True,
            )

            modified = []
            untracked = []
            for line in status_res.stdout.splitlines():
                if not line.strip():
                    continue
                code, path = line[:2].strip(), line[3:].strip()
                if code == "??":
                    untracked.append(path)
                else:
                    modified.append(path)

            return {
                "initialized": True,
                "branch": branch_res.stdout.strip() or "main",
                "modified": modified,
                "untracked": untracked,
            }
        except subprocess.SubprocessError:
            return {"initialized": True, "branch": "unknown", "modified": [], "untracked": []}

    def get_git_diff(self, project_id: str, base_branch: str = "main") -> str:
        """Get the diff between the current branch and the base branch."""
        project_dir = self.get_project_dir(project_id)
        if not (project_dir / ".git").exists():
            return ""

        try:
            diff_res = subprocess.run(
                ["git", "diff", base_branch],
                cwd=project_dir,
                capture_output=True,
                check=True,
                text=True,
            )
            return diff_res.stdout
        except subprocess.SubprocessError:
            return ""


# Global singleton instance
_workspace_service: WorkspaceService | None = None


def get_workspace_service() -> WorkspaceService:
    global _workspace_service
    if _workspace_service is None:
        _workspace_service = WorkspaceService()
    return _workspace_service

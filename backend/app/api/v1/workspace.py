"""
Workspace & Filesystem API endpoints.

  GET  /api/v1/projects/{project_id}/files          — list project workspace files
  GET  /api/v1/projects/{project_id}/files/content  — get specific file content
  GET  /api/v1/projects/{project_id}/git/status     — git branch and working tree status
  GET  /api/v1/projects/{project_id}/git/diff       — git diff
  POST /api/v1/projects/{project_id}/runner/execute — run verification command in workspace
"""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.db_models import Project
from app.services.runner import get_execution_runner
from app.services.workspace import PathTraversalError, get_workspace_service

logger = logging.getLogger(__name__)
router = APIRouter(tags=["workspace"])


class CommandExecutionRequest(BaseModel):
    command: list[str] = Field(
        ...,
        description="Command and arguments list (e.g. ['python', '-m', 'pytest'])",
        min_length=1,
    )
    timeout: int = Field(default=30, ge=5, le=120)


async def _get_project_or_404(db: AsyncSession, project_id: str) -> Project:
    project = await db.get(Project, project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "project_not_found", "message": f"Project '{project_id}' not found."},
        )
    return project


@router.get(
    "/projects/{project_id}/files",
    summary="List all source files in the project workspace",
)
async def list_workspace_files(
    project_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    subpath: str = Query(default="", description="Optional subfolder to list"),
) -> dict[str, Any]:
    await _get_project_or_404(db, project_id)
    workspace = get_workspace_service()

    try:
        files = workspace.list_files(project_id, subpath=subpath)
        return {
            "project_id": project_id,
            "total": len(files),
            "files": [
                {
                    "path": f.path,
                    "size_bytes": f.size_bytes,
                    "modified_at": f.modified_at,
                }
                for f in files
            ],
        }
    except PathTraversalError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "path_traversal", "message": str(exc)},
        ) from exc


@router.get(
    "/projects/{project_id}/files/content",
    summary="Get content of a file in the project workspace",
)
async def get_workspace_file_content(
    project_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    path: str = Query(..., description="Relative file path within project root"),
) -> dict[str, Any]:
    await _get_project_or_404(db, project_id)
    workspace = get_workspace_service()

    try:
        content = workspace.read_file(project_id, path)
        return {
            "project_id": project_id,
            "path": path,
            "content": content,
            "size_bytes": len(content.encode("utf-8")),
        }
    except PathTraversalError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "path_traversal", "message": str(exc)},
        ) from exc
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "file_not_found", "message": f"File '{path}' not found in workspace."},
        ) from exc


@router.get(
    "/projects/{project_id}/git/status",
    summary="Get Git status of the project repository",
)
async def get_git_status(
    project_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    await _get_project_or_404(db, project_id)
    workspace = get_workspace_service()
    status_info = workspace.get_git_status(project_id)
    return {
        "project_id": project_id,
        **status_info,
    }


@router.get(
    "/projects/{project_id}/git/diff",
    summary="Get Git diff of the project repository",
)
async def get_git_diff(
    project_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    base_branch: str = Query(default="main"),
) -> dict[str, Any]:
    await _get_project_or_404(db, project_id)
    workspace = get_workspace_service()
    diff_text = workspace.get_git_diff(project_id, base_branch=base_branch)
    return {
        "project_id": project_id,
        "base_branch": base_branch,
        "diff": diff_text,
    }


@router.post(
    "/projects/{project_id}/runner/execute",
    summary="Execute a safe check or test command in the project workspace",
)
async def execute_command(
    project_id: str,
    payload: CommandExecutionRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    await _get_project_or_404(db, project_id)
    runner = get_execution_runner()

    result = runner.run_command(
        project_id,
        payload.command,
        timeout=payload.timeout,
    )

    return {
        "project_id": project_id,
        "command": result.command,
        "exit_code": result.exit_code,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "duration_seconds": result.duration_seconds,
        "timed_out": result.timed_out,
        "success": result.success,
    }

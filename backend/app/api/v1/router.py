"""API v1 router — aggregates all v1 endpoint routers."""

from fastapi import APIRouter

from app.api.v1 import health, monitoring, projects, qa_security, workflow, workspace

router = APIRouter(prefix="/api/v1")

router.include_router(health.router)
router.include_router(projects.router)
router.include_router(workflow.router)
router.include_router(workspace.router)
router.include_router(qa_security.router)
router.include_router(monitoring.router)

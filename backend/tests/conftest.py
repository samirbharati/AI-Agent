"""
pytest configuration and shared fixtures.

Key design decisions:
  - Tests use an in-memory SQLite database to avoid touching the real DB.
  - Ollama is NOT required for any unit tests.
  - The settings cache is cleared before each test to allow environment
    overrides via environment variables.
  - The SQLAlchemy engine is reset before each test to point at the
    in-memory test database.
  - Each test gets a fresh database (tables re-created per test function).
"""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

# ---------------------------------------------------------------------------
# Force test environment BEFORE importing app modules.
# This ensures Settings picks up test overrides.
# ---------------------------------------------------------------------------

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("OLLAMA_BASE_URL", "http://localhost:11434")
os.environ.setdefault("OLLAMA_MODEL", "qwen2.5-coder:7b")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")


@pytest.fixture(autouse=True)
def reset_settings_cache():
    """Clear the Settings LRU cache before each test."""
    from app.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def reset_db_engine(reset_settings_cache):
    """
    Reset the SQLAlchemy engine before each test.

    This ensures a fresh in-memory database connection is created
    for every test function.
    """
    from app.database.base import reset_engine

    reset_engine()
    yield
    reset_engine()


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Provide a database session backed by an in-memory SQLite database.

    Tables are created fresh for each test and torn down afterward.
    """
    from app.database.base import Base, get_engine
    from app.database.init_db import init_db

    engine = get_engine()

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed agent definitions
    await init_db()

    from app.database.base import get_session_factory

    factory = get_session_factory()
    async with factory() as session:
        yield session

    # Drop all tables after the test
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def async_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Provide an AsyncClient that hits the real FastAPI app with a test DB.

    The lifespan is bypassed — the test db_session fixture already handles
    DB setup and teardown. We override the `get_db` dependency to inject
    the test session directly.
    """
    from app.api.deps import get_db
    from app.main import create_app
    from fastapi import FastAPI

    app: FastAPI = create_app()

    # Override the DB dependency to use the test session
    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    # Use lifespan=False to skip DB init (handled by db_session fixture)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()

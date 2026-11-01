"""
SQLAlchemy async engine, session factory, and base declarative class.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

# ---------------------------------------------------------------------------
# Declarative base
# ---------------------------------------------------------------------------


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""


# ---------------------------------------------------------------------------
# Engine & session factory (lazy — created on first access)
# ---------------------------------------------------------------------------

_engine = None
_async_session_factory = None


def get_engine():
    """Return (or create) the async SQLAlchemy engine."""
    global _engine  # noqa: PLW0603
    if _engine is None:
        settings = get_settings()
        connect_args = {}
        if "sqlite" in settings.database_url:
            connect_args["check_same_thread"] = False
        _engine = create_async_engine(
            settings.database_url,
            echo=settings.is_development,
            connect_args=connect_args,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return (or create) the async session factory."""
    global _async_session_factory  # noqa: PLW0603
    if _async_session_factory is None:
        _async_session_factory = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )
    return _async_session_factory


def reset_engine() -> None:
    """
    Reset the engine and session factory.

    Call this in tests after swapping the DATABASE_URL so that a new engine
    is created pointing at the test database.
    """
    global _engine, _async_session_factory  # noqa: PLW0603
    _engine = None
    _async_session_factory = None

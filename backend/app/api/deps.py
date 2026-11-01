"""FastAPI dependency injectors."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.base import get_session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Yield an async database session.

    Commits on success, rolls back on exception. Always closes the session.
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

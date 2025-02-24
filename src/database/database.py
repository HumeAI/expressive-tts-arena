"""
database.py

This module sets up the SQLAlchemy database connection for the Expressive TTS Arena project.
It initializes the PostgreSQL engine, creates a session factory for handling database transactions,
and defines a declarative base class for ORM models.

If no DATABASE_URL environment variable is set, then create a dummy database to fail gracefully.
"""

# Standard Library Imports
from typing import Callable, Optional

# Third-Party Library Imports
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

# Local Application Imports
from src.config import Config


# Define the SQLAlchemy Base using SQLAlchemy 2.0 style.
class Base(DeclarativeBase):
    pass


engine: Optional[AsyncEngine] = None


class AsyncDummySession:
    is_dummy = True  # Flag to indicate this is a dummy session.

    async def __enter__(self):
        return self

    async def __exit__(self, exc_type, exc_value, traceback):
        pass

    async def add(self, _instance, _warn=True):
        # No-op: simply ignore adding the instance.
        pass

    async def commit(self):
        # Raise an exception to simulate failure when attempting a write.
        raise RuntimeError("DummySession does not support commit operations.")

    async def refresh(self, _instance):
        # Raise an exception to simulate failure when attempting to refresh.
        raise RuntimeError("DummySession does not support refresh operations.")

    async def rollback(self):
        # No-op: there's nothing to roll back.
        pass

    async def close(self):
        # No-op: nothing to close.
        pass


# AsyncDBSessionMaker is either a async_sessionmaker instance or a callable that returns a AsyncDummySession.
AsyncDBSessionMaker = async_sessionmaker | Callable[[], AsyncDummySession]


def init_db(config: Config) -> AsyncDBSessionMaker:
    """
    Initialize the database engine and return a session factory based on the provided configuration.

    In production, a valid DATABASE_URL is required. In development, if a DATABASE_URL is provided,
    it is used; otherwise, a dummy session factory is returned to allow graceful failure.

    Args:
        config (Config): The application configuration.

    Returns:
        AsyncDBSessionMaker: A sessionmaker bound to the engine, or a dummy session factory.
    """
    # ruff doesn't like setting global variables, but this is practical here
    global engine  # noqa

    # Convert standard PostgreSQL URL to async format
    def convert_to_async_url(url: str) -> str:
        # Convert postgresql:// to postgresql+asyncpg://
        if url.startswith('postgresql://'):
            return url.replace('postgresql://', 'postgresql+asyncpg://', 1)
        return url

    if config.app_env == "prod":
        # In production, a valid DATABASE_URL is required.
        if not config.database_url:
            raise ValueError("DATABASE_URL must be set in production!")
        async_db_url = convert_to_async_url(config.database_url)
        engine = create_async_engine(async_db_url)
        return async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)

    # In development, if a DATABASE_URL is provided, use it.
    if config.database_url:
        async_db_url = convert_to_async_url(config.database_url)
        engine = create_async_engine(async_db_url)
        return async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)

    # No DATABASE_URL is provided; use a DummySession that does nothing.
    engine = None

    def async_dummy_session_factory() -> AsyncDummySession:
        return AsyncDummySession()

    return async_dummy_session_factory


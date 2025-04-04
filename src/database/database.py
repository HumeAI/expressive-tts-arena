# Standard Library Imports
from typing import Callable, Optional, TypeAlias, Union

# Third-Party Library Imports
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

# Local Application Imports
from src.common import Config, logger


# Define the SQLAlchemy Base
class Base(DeclarativeBase):
    pass

class DummyAsyncSession:
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
        raise RuntimeError("DummyAsyncSession does not support commit operations.")

    async def refresh(self, _instance):
        # Raise an exception to simulate failure when attempting to refresh.
        raise RuntimeError("DummyAsyncSession does not support refresh operations.")

    async def rollback(self):
        # No-op: there's nothing to roll back.
        pass

    async def close(self):
        # No-op: nothing to close.
        pass

AsyncDBSessionMaker: TypeAlias = Union[async_sessionmaker[AsyncSession], Callable[[], DummyAsyncSession]]
engine: Optional[AsyncEngine] = None

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

    if config.app_env == "prod":
        # In production, a valid DATABASE_URL is required.
        if not config.database_url:
            raise ValueError("DATABASE_URL must be set in production!")

        async_db_url = config.database_url
        engine = create_async_engine(async_db_url)

        return async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)

    # In development, if a DATABASE_URL is provided, use it.
    if config.database_url:
        async_db_url = config.database_url
        engine = create_async_engine(async_db_url)

        return async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)

    # No DATABASE_URL is provided; use a DummyAsyncSession that does nothing.
    engine = None
    logger.warning("No DATABASE_URL provided - database operations will use DummyAsyncSession")

    def async_dummy_session_factory() -> DummyAsyncSession:
        return DummyAsyncSession()

    return async_dummy_session_factory

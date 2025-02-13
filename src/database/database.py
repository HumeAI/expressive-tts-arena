"""
database.py

This module sets up the SQLAlchemy database connection for the Expressive TTS Arena project.
It initializes the PostgreSQL engine, creates a session factory for handling database transactions,
and defines a declarative base class for ORM models.

If no DATABASE_URL environment variable is set, then create a dummy database to fail gracefully
"""

# Standard Library Imports
from typing import Callable, Optional

# Third-Party Library Imports
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Local Application Imports
from src.config import Config


class DummySession:
    is_dummy = True  # Flag to indicate this is a dummy session.

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass

    def add(self, _instance, _warn=True):
        # No-op: simply ignore adding the instance.
        pass

    def commit(self):
        # Raise an exception to simulate failure when attempting a write.
        raise RuntimeError("DummySession does not support commit operations.")

    def refresh(self, _instance):
        # Raise an exception to simulate failure when attempting to refresh.
        raise RuntimeError("DummySession does not support refresh operations.")

    def rollback(self):
        # No-op: there's nothing to roll back.
        pass

    def close(self):
        # No-op: nothing to close.
        pass


Base = declarative_base()
engine: Optional[Engine] = None

DBSessionMaker = sessionmaker | Callable[[], DummySession]


def init_db(config: Config) -> DBSessionMaker:
    # ruff doesn't like setting global variables, but this is practical here
    global engine # noqa 

    if config.app_env == "prod":
        # In production, a valid DATABASE_URL is required.
        if not config.database_url:
            raise ValueError("DATABASE_URL must be set in production!")

        engine = create_engine(config.database_url)
        return sessionmaker(bind=engine)
    # In development, if a DATABASE_URL is provided, use it.
    if config.database_url:
        engine = create_engine(config.database_url)
        return sessionmaker(bind=engine)
    # No DATABASE_URL is provided; use a DummySession that does nothing.
    engine = None

    def dummy_session_factory():
        return DummySession()

    return dummy_session_factory

"""
init_db.py

This script initializes the database by creating all tables defined in the ORM models.
It uses async SQLAlchemy operations to create tables in the PostgreSQL database.
Run this script once to set up your database schema.
"""

# Standard Library Imports
import asyncio

# Local Application Imports
from src.config import Config, logger
from src.database.database import engine
from src.database.models import Base


async def init_db_async():
    """
    Asynchronously create all database tables defined in the ORM models.

    This function connects to the database using the configured async engine
    and creates all tables that are mapped to SQLAlchemy models derived from
    the Base class. It uses SQLAlchemy's create_all method with the async
    engine context.

    Returns:
        None
    """
    async with engine.begin() as conn:
        # In SQLAlchemy 2.0 with async, we use the connection directly
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database tables created successfully using async SQLAlchemy.")


def main():
    """
    Main entry point for the database initialization script.

    This function creates the configuration, ensures the async engine is 
    initialized, and runs the async initialization function within an
    event loop.

    Returns:
        None
    """
    # Make sure config is loaded first to initialize the engine
    Config.get()

    # Run the async initialization function
    asyncio.run(init_db_async())


if __name__ == "__main__":
    main()

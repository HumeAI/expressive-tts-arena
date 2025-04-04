"""
init_db_direct.py

A simplified script to initialize the database by creating all tables.
"""

# Standard Library Imports
import asyncio
import sys

# Third-Party Library Imports
from sqlalchemy.ext.asyncio import create_async_engine

# Local Application Imports
from src.common import Config, logger
from src.database import Base


async def init_tables():
    config = Config.get()
    database_url = config.database_url

    if not database_url:
        logger.error("DATABASE_URL is not set in environment variables")
        return False

    engine = create_async_engine(database_url, echo=config.debug)

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        logger.info("Database tables created successfully!")
        return True
    except Exception as e:
        logger.error(f"Error creating tables: {e}")
        return False
    finally:
        await engine.dispose()


if __name__ == "__main__":
    success = asyncio.run(init_tables())
    sys.exit(0 if success else 1)

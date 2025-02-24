"""
test_db.py

This script verifies the database connection for the Expressive TTS Arena project.
It attempts to connect to the PostgreSQL database using async SQLAlchemy and executes 
a simple query to confirm connectivity.

Functionality:
- Loads the database connection from `database.py`.
- Attempts to establish an async connection to the database.
- Executes a test query (`SELECT 1`) to confirm connectivity.
- Prints a success message if the connection is valid.
- Prints an error message if the connection fails.

Usage:
    python src/test_db.py

Expected Output:
    Database connection successful!  (if the database is reachable)
    Database connection failed: <error message> (if there are connection issues)

Troubleshooting:
- Ensure the `.env` file contains a valid `DATABASE_URL`.
- Check that the database server is running and accessible.
- Verify PostgreSQL credentials and network settings.
"""

# Standard Library Imports
import asyncio
import sys

# Third-Party Library Imports
from sqlalchemy import text

# Local Application Imports
from src.config import Config, logger
from src.database.database import engine, init_db


async def test_connection_async():
    """
    Asynchronously test the database connection.

    This function attempts to connect to the database using the configured
    async engine and execute a simple SELECT query. It logs success or failure
    messages accordingly.

    Returns:
        bool: True if the connection was successful, False otherwise.
    """
    if engine is None:
        logger.error("No valid database engine configured.")
        return False

    try:
        # Create a new async session
        async with engine.connect() as conn:
            # Execute a simple query to verify connectivity
            result = await conn.execute(text("SELECT 1"))
            # Fetch the result to make sure the query completes
            await result.fetchone()

        logger.info("Async database connection successful!")
        return True

    except Exception as e:
        logger.error(f"Async database connection failed: {e}")
        return False


def main():
    """
    Main entry point for the database connection test script.

    This function creates the configuration, initializes the database engine,
    and runs the async test function within an event loop. It exits with an
    appropriate system exit code based on the test result.

    Returns:
        None
    """
    # Make sure config is loaded first to initialize the engine
    config = Config.get()

    # Initialize the database engine
    init_db(config)

    # Run the async test function
    success = asyncio.run(test_connection_async())

    # Exit with an appropriate status code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

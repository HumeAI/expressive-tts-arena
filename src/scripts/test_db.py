"""
test_db.py

This script verifies the database connection for the Expressive TTS Arena project.
It attempts to connect to the PostgreSQL database using SQLAlchemy and executes a simple query.

Functionality:
- Loads the database connection from `database.py`.
- Attempts to establish a connection to the database.
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
import sys

# Third-Party Library Imports
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

# Local Application Imports
from src.config import logger
from src.database import engine


def main() -> None:
    if engine is None:
        logger.error("No valid database engine configured.")
        sys.exit(1)

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            logger.info("Database connection successful!")
    except OperationalError as e:
        logger.error(f"Database connection failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

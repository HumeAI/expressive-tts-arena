"""
init_db.py

This script initializes the database by creating all tables defined in the ORM models.
Run this script once to create your tables in the PostgreSQL database.
"""

# Local Application Imports
from src.config import logger
from src.database.database import engine
from src.database.models import Base


def init_db():
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully.")


if __name__ == "__main__":
    init_db()

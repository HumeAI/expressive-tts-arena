"""
database.py

This module sets up the SQLAlchemy database connection for the Expressive TTS Arena project.
It initializes the PostgreSQL engine, creates a session factory for handling database transactions,
and defines a declarative base class for ORM models.
"""

# Third-Party Library Imports
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Local Application Imports
from src.config import validate_env_var

# Validate and retrieve the database URL from environment variables
DATABASE_URL = validate_env_var("DATABASE_URL")

# Create the database engine using the validated URL
engine = create_engine(DATABASE_URL)

# Create a session factory for database transactions
SessionLocal = sessionmaker(bind=engine)

# Declarative base class for ORM models
Base = declarative_base()

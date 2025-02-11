"""
config.py

Global configuration and logger setup for the project.

Key Features:
- Uses environment variables defined in the system (Docker in production).
- Loads a `.env` file only in development to simulate production variables locally.
- Configures the logger for consistent logging across all modules.
- Dynamically enables DEBUG logging in development and INFO logging in production (unless overridden).
"""

# Standard Library Imports
import logging
import os

# Third-Party Library Imports
from dotenv import load_dotenv


# Determine the environment (defaults to "dev" if not explicitly set)
APP_ENV = os.getenv("APP_ENV", "dev").lower()
if APP_ENV not in {"dev", "prod"}:
    print(f'Warning: Invalid APP_ENV "{APP_ENV}". Defaulting to "dev".')
    APP_ENV = "dev"


# In development, load environment variables from .env file (not used in production)
if APP_ENV == "dev":
    if os.path.exists(".env"):
        # Load environment variables
        load_dotenv(".env", override=True)
    else:
        print("Warning: .env file not found. Using system environment variables.")


# Enable debug mode if in development (or if explicitly set in env variables)
DEBUG = APP_ENV == "dev" or os.getenv("DEBUG", "false").lower() == "true"

# Configure the logger
logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger: logging.Logger = logging.getLogger("tts_arena")
logger.info(f'App running in "{APP_ENV}" mode.')
logger.info(f'Debug mode is {"enabled" if DEBUG else "disabled"}.')

if DEBUG:
    logger.debug(f"DEBUG mode enabled.")


# Define the directory for audio files relative to the project root
AUDIO_DIR = os.path.join(os.getcwd(), "static", "audio")
os.makedirs(AUDIO_DIR, exist_ok=True)
logger.info(f"Audio directory set to {AUDIO_DIR}")

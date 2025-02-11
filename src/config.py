"""
config.py

Global configuration and logger setup for the project.

Key Features:
- Loads environment variables
- Configures the logger for consistent logging across all modules.
- Dynamically sets the logging level based on the DEBUG environment variable.
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


# Enable debugging mode based on an environment variable
debug_raw = os.getenv("DEBUG", "false").lower()
if debug_raw not in {"true", "false"}:
    print(f'Warning: Invalid DEBUG value "{debug_raw}". Defaulting to "false".')
DEBUG = debug_raw == "true"


# Configure the logger
logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger: logging.Logger = logging.getLogger("tts_arena")
logger.info(f'Debug mode is {"enabled" if DEBUG else "disabled"}.')

if DEBUG:
    logger.debug(f"DEBUG mode enabled.")


# Define the directory for audio files relative to the project root
AUDIO_DIR = os.path.join(os.getcwd(), "static", "audio")
os.makedirs(AUDIO_DIR, exist_ok=True)
logger.info(f"Audio directory set to {AUDIO_DIR}")

"""
config.py

Global configuration and logger setup for the project.

Key Features:
- Loads environment variables
- Configures the logger for consistent logging across all modules.
- Dynamically sets the logging level based on the DEBUG environment variable.
"""

# Standard Library Imports
import atexit
import logging
import os

# Third-Party Library Imports
from dotenv import load_dotenv


# Load environment variables
load_dotenv(override=True)


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

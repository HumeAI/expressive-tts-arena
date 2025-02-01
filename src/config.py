"""
config.py

Global configuration and logger setup for the project. This file centralizes shared
constants and settings, such as the logging configuration and API constraints.

Key Features:
- Configures the logger for consistent logging across all modules.
- Dynamically sets the logging level based on the DEBUG environment variable.
"""

# Standard Library Imports
import logging
import os

# Third-Party Library Imports
from dotenv import load_dotenv


# Load environment variables
load_dotenv()


# Enable debugging mode based on an environment variable
debug_raw = os.getenv('DEBUG', 'false').lower()
if debug_raw not in {'true', 'false'}:
    print(f'Warning: Invalid DEBUG value "{debug_raw}". Defaulting to "false".')
DEBUG = debug_raw == 'true'


# Configure the logger
logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger: logging.Logger = logging.getLogger('tts_arena')
logger.info(f'Debug mode is {"enabled" if DEBUG else "disabled"}.')

if DEBUG:
    logger.debug(f'DEBUG mode enabled.')
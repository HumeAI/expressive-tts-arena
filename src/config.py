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
from pathlib import Path

# Third-Party Library Imports
from dotenv import load_dotenv

# Determine the environment (defaults to "dev" if not explicitly set)
APP_ENV = os.getenv("APP_ENV", "dev").lower()
if APP_ENV not in {"dev", "prod"}:
    APP_ENV = "dev"


# In development, load environment variables from .env file (not used in production)
if APP_ENV == "dev" and Path(".env").exists():
    load_dotenv(".env", override=True)


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
    logger.debug("DEBUG mode enabled.")


# Define the directory for audio files relative to the project root
AUDIO_DIR = Path.cwd() / "static" / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)
logger.info(f"Audio directory set to {AUDIO_DIR}")


def validate_env_var(var_name: str) -> str:
    """
    Validates that an environment variable is set and returns its value.

    Args:
        var_name (str): The name of the environment variable to validate.

    Returns:
        str: The value of the environment variable.

    Raises:
        ValueError: If the environment variable is not set.

    Examples:
        >>> import os
        >>> os.environ["EXAMPLE_VAR"] = "example_value"
        >>> validate_env_var("EXAMPLE_VAR")
        'example_value'

        >>> validate_env_var("MISSING_VAR")
        Traceback (most recent call last):
          ...
        ValueError: MISSING_VAR is not set. Please ensure it is defined in your environment variables.
    """
    value = os.environ.get(var_name, "")
    if not value:
        raise ValueError(
            f"{var_name} is not set. Please ensure it is defined in your environment variables."
        )
    return value

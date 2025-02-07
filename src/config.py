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
import shutil

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


def cleanup_audio_directory_contents() -> None:
    """
    Delete all audio files within AUDIO_DIR, leaving the directory intact.

    This function is intended to be registered to run when the application exits.
    It assumes that AUDIO_DIR contains only audio files (or symbolic links), and no subdirectories.
    """
    if not os.path.exists(AUDIO_DIR):
        logger.info(
            "Audio directory %s does not exist. Nothing to clean up.", AUDIO_DIR
        )
        return

    # Use os.scandir for efficient directory iteration.
    with os.scandir(AUDIO_DIR) as entries:
        for entry in entries:
            if entry.is_file() or entry.is_symlink():
                try:
                    os.unlink(entry.path)
                    logger.info("Deleted file: %s", entry.path)
                except Exception as exc:
                    logger.error(
                        "Failed to delete file %s. Reason: %s", entry.path, exc
                    )
            else:
                logger.warning("Skipping non-file entry: %s", entry.path)


# Register the cleanup function to be called on normal program termination.
atexit.register(cleanup_audio_directory_contents)

# Standard Library Imports
import base64
import os
import time
from pathlib import Path

# Local Application Imports
from .config import Config, logger


def _delete_files_older_than(directory: Path, minutes: int = 30) -> None:
    """
    Delete all files in the specified directory that are older than a given number of minutes.

    This function checks each file in the given directory and removes it if its last modification
    time is older than the specified threshold. By default, the threshold is set to 30 minutes.

    Args:
        directory (str): The path to the directory where files will be checked and possibly deleted.
        minutes (int, optional): The age threshold in minutes. Files older than this will be deleted.
                                 Defaults to 30 minutes.

    Returns: None
    """
    # Get the current time in seconds since the epoch.
    now = time.time()
    # Convert the minutes threshold to seconds.
    cutoff = now - (minutes * 60)
    dir_path = Path(directory)

    # Iterate over all files in the directory.
    for file_path in dir_path.iterdir():
        if file_path.is_file():
            file_mod_time = file_path.stat().st_mtime
            # If the file's modification time is older than the cutoff, delete it.
            if file_mod_time < cutoff:
                try:
                    file_path.unlink()
                    logger.info(f"Deleted: {file_path}")
                except Exception as e:
                    logger.exception(f"Error deleting {file_path}: {e}")

def save_base64_audio_to_file(base64_audio: str, filename: str, config: Config) -> str:
    """
    Decode a base64-encoded audio string and write the resulting binary data to a file
    within the preconfigured AUDIO_DIR directory. Prior to writing the bytes to an audio
    file, all files within the directory that are more than 30 minutes old are deleted.
    This function verifies the file was created, logs both the absolute and relative
    file paths, and returns a path relative to the current working directory
    (as required by Gradio for serving static files).

    Args:
        base64_audio (str): The base64-encoded string representing the audio data.
        filename (str): The name of the file (including extension, e.g.,
                        'b4a335da-9786-483a-b0a5-37e6e4ad5fd1.mp3') where the decoded
                        audio will be saved.

    Returns:
        str: The relative file path to the saved audio file.

    Raises:
        FileNotFoundError: If the audio file was not created.
    """

    audio_bytes = base64.b64decode(base64_audio)
    file_path = Path(config.audio_dir) / filename
    num_minutes = 30

    _delete_files_older_than(config.audio_dir, num_minutes)

    # Write the binary audio data to the file.
    with file_path.open("wb") as audio_file:
        audio_file.write(audio_bytes)

    # Verify that the file was created.
    if not file_path.exists():
        raise FileNotFoundError(f"Audio file was not created at {file_path}")

    # Compute a relative path for Gradio to serve (relative to the current working directory).
    relative_path = file_path.relative_to(Path.cwd())
    logger.debug(f"Audio file absolute path: {file_path}")
    logger.debug(f"Audio file relative path: {relative_path}")

    return str(relative_path)

def validate_env_var(var_name: str) -> str:
    """
    Validates that an environment variable is set and returns its value.

    Args:
        var_name (str): The name of the environment variable to validate.

    Returns:
        str: The value of the environment variable.

    Raises:
        ValueError: If the environment variable is not set.
    """
    value = os.environ.get(var_name, "")
    if not value:
        raise ValueError(f"{var_name} is not set. Please ensure it is defined in your environment variables.")
    return value


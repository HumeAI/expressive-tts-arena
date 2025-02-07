"""
utils.py

This file contains utility functions that are shared across the project.
These functions provide reusable logic to simplify code in other modules.

Functions:
- truncate_text: Truncates a string to a specified length with ellipses. (used for logging)
- validate_env_var: Ensures the presence of a specific environment variable and retrieves its value.
- validate_character_description_length: Ensures that a voice description does not exceed the specified minimum or maximum length.
"""

# Standard Library Imports
import base64
import os

# Local Application Imports
from src.config import AUDIO_DIR, logger
from src.constants import (
    CHARACTER_DESCRIPTION_MIN_LENGTH,
    CHARACTER_DESCRIPTION_MAX_LENGTH,
)


def truncate_text(text: str, max_length: int = 50) -> str:
    """
    Truncate a string to the specified length, appending ellipses if necessary.

    Args:
        text (str): The text to truncate.
        max_length (int): The maximum length of the truncated string.

    Returns:
        str: The truncated text.

    Examples:
        >>> truncate_text("Hello, World!", 5)
        'Hello...'
        >>> truncate_text("Short string", 20)
        'Short string'
        >>> truncate_text("Edge case with zero length", 0)
        ''
    """
    if max_length <= 0:
        logger.warning(f"Invalid max_length={max_length}. Returning empty string.")
        return ""

    is_truncated = len(text) > max_length
    if is_truncated:
        logger.debug(f"Truncated text to {max_length} characters.")

    return text[:max_length] + ("..." if is_truncated else "")


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


def validate_character_description_length(character_description: str) -> None:
    """
    Validates that a voice description is within specified minimum and maximum length limits.

    Args:
        character_description (str): The input character description to validate.

    Raises:
        ValueError: If the character description is empty, too short, or exceeds max length.

    Example:
        >>> validate_character_description_length("This is a character description.")
        # Passes validation

        >>> validate_character_description_length("")
        # Raises ValueError: "Voice Description must be at least 20 characters long."
    """
    stripped_character_description = character_description.strip()
    character_description_length = len(stripped_character_description)

    logger.debug(
        f"Voice description length being validated: {character_description_length} characters"
    )

    if character_description_length < CHARACTER_DESCRIPTION_MIN_LENGTH:
        raise ValueError(
            f"Your character description is too short. Please enter at least {CHARACTER_DESCRIPTION_MIN_LENGTH} characters. "
            f"(Current length: {character_description_length})"
        )
    if character_description_length > CHARACTER_DESCRIPTION_MAX_LENGTH:
        raise ValueError(
            f"Your character description is too long. Please limit it to {CHARACTER_DESCRIPTION_MAX_LENGTH} characters. "
            f"(Current length: {character_description_length})"
        )
    logger.debug(
        f"Character description length validation passed for character_description: {truncate_text(stripped_character_description)}"
    )


def save_base64_audio_to_file(base64_audio: str, filename: str) -> str:
    """
    Decode a base64-encoded audio string and write the resulting binary data to a file
    within the preconfigured AUDIO_DIR directory. This function verifies the file was created,
    logs the absolute and relative file paths, and returns a path relative to the current
    working directory (which is what Gradio requires to serve static files).

    Args:
        base64_audio (str): The base64-encoded string representing the audio data.
        filename (str): The name of the file (including extension, e.g.,
                        'b4a335da-9786-483a-b0a5-37e6e4ad5fd1.mp3') where the decoded
                        audio will be saved.

    Returns:
        str: The relative file path to the saved audio file.

    Raises:
        Exception: Propagates any exceptions raised during the decoding or file I/O operations.
    """
    # Decode the base64-encoded audio into binary data.
    audio_bytes = base64.b64decode(base64_audio)

    # Construct the full absolute file path within the AUDIO_DIR directory.
    file_path = os.path.join(AUDIO_DIR, filename)

    # Write the binary audio data to the file.
    with open(file_path, "wb") as audio_file:
        audio_file.write(audio_bytes)

    # Verify that the file was created.
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Audio file was not created at {file_path}")

    # Compute a relative path for Gradio to serve (relative to the project root).
    relative_path = os.path.relpath(file_path, os.getcwd())
    logger.debug(f"Audio file absolute path: {file_path}")
    logger.debug(f"Audio file relative path: {relative_path}")

    return relative_path

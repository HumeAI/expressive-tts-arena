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
import random
import time
from typing import Tuple

# Local Application Imports
from src import constants
from src.config import AUDIO_DIR, logger
from src.types import ComparisonType, Option, OptionMap, TTSProviderName


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

    if character_description_length < constants.CHARACTER_DESCRIPTION_MIN_LENGTH:
        raise ValueError(
            f"Your character description is too short. Please enter at least {constants.CHARACTER_DESCRIPTION_MIN_LENGTH} characters. "
            f"(Current length: {character_description_length})"
        )
    if character_description_length > constants.CHARACTER_DESCRIPTION_MAX_LENGTH:
        raise ValueError(
            f"Your character description is too long. Please limit it to {constants.CHARACTER_DESCRIPTION_MAX_LENGTH} characters. "
            f"(Current length: {character_description_length})"
        )
    logger.debug(
        f"Character description length validation passed for character_description: {truncate_text(stripped_character_description)}"
    )


def delete_files_older_than(directory: str, minutes: int = 30) -> None:
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

    # Iterate over all files in the directory.
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        file_mod_time = os.path.getmtime(file_path)
        # If the file's modification time is older than the cutoff, delete it.
        if file_mod_time < cutoff:
            try:
                os.remove(file_path)
                print(f"Deleted: {file_path}")
            except Exception as e:
                print(f"Error deleting {file_path}: {e}")


def save_base64_audio_to_file(base64_audio: str, filename: str) -> str:
    """
    Decode a base64-encoded audio string and write the resulting binary data to a file
    within the preconfigured AUDIO_DIR directory. Prior to writing the bytes to an audio
    file all files within the directory which are more than 30 minutes old are deleted.
    This function verifies the file was created, logs the absolute and relative file
    paths, and returns a path relative to the current working directory (which is what
    Gradio requires to serve static files).

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

    # Delete all audio files older than 30 minutes before writing new audio file.
    num_minutes = 30
    delete_files_older_than(AUDIO_DIR, num_minutes)

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


def choose_providers(
    text_modified: bool,
    character_description: str,
) -> Tuple[ComparisonType, TTSProviderName, TTSProviderName]:
    """
    Select two TTS providers based on whether the text has been modified.

    The first provider is always set to "Hume AI". For the second provider, the function
    selects "Hume AI" if the text has been modified or if a character description was
    not provided; otherwise, it randomly chooses one from the TTS_PROVIDERS list.

    Args:
        text_modified (bool): A flag indicating whether the text has been modified.
            - If True, both providers will be "Hume AI".
            - If False, the second provider is randomly selected from TTS_PROVIDERS.

    Returns:
        Tuple[TTSProviderName, TTSProviderName]: A tuple containing two TTS provider names,
        where the first is always "Hume AI" and the second is determined by the text_modified
        flag and random selection.
    """
    hume_comparison_only = text_modified or not character_description

    provider_a = constants.HUME_AI
    provider_b = (
        constants.HUME_AI
        if hume_comparison_only
        else random.choice(constants.TTS_PROVIDERS)
    )

    match provider_b:
        case constants.HUME_AI:
            comparison_type = constants.HUME_TO_HUME
        case constants.ELEVENLABS:
            comparison_type = constants.HUME_TO_ELEVENLABS

    return comparison_type, provider_a, provider_b


def create_shuffled_tts_options(
    provider_a: TTSProviderName,
    audio_a: str,
    generation_id_a: str,
    provider_b: TTSProviderName,
    audio_b: str,
    generation_id_b: str,
) -> Tuple[str, str, str, str, OptionMap]:
    """
    Create and shuffle TTS generation options.

    This function creates two Option instances from the provided TTS details, shuffles them,
    and then extracts the audio file paths and generation IDs from the shuffled options.
    It also returns a mapping from option constants to the corresponding TTS providers.

    Args:
        provider_a (TTSProviderName): The TTS provider for the first generation.
        audio_a (str): The relative file path to the audio file for the first generation.
        generation_id_a (str): The generation ID for the first generation.
        provider_b (TTSProviderName): The TTS provider for the second generation.
        audio_b (str): The relative file path to the audio file for the second generation.
        generation_id_b (str): The generation ID for the second generation.

    Returns:
        Tuple[str, str, str, str, OptionMap]:
            A tuple containing:
            - option_a_audio (str): Audio file path for the first shuffled option.
            - option_b_audio (str): Audio file path for the second shuffled option.
            - option_a_generation_id (str): Generation ID for the first shuffled option.
            - option_b_generation_id (str): Generation ID for the second shuffled option.
            - options_map (OptionMap): Mapping from option constants to their TTS providers.
    """
    # Create a list of Option instances for the available providers.
    options = [
        Option(provider=provider_a, audio=audio_a, generation_id=generation_id_a),
        Option(provider=provider_b, audio=audio_b, generation_id=generation_id_b),
    ]

    # Randomly shuffle the list of options.
    random.shuffle(options)

    # Unpack the two options.
    option_a, option_b = options

    # Extract audio file paths and generation IDs.
    option_a_audio = option_a.audio
    option_b_audio = option_b.audio
    option_a_generation_id = option_a.generation_id
    option_b_generation_id = option_b.generation_id

    # Build a mapping from option constants to the corresponding providers.
    options_map: OptionMap = {
        constants.OPTION_A: option_a.provider,
        constants.OPTION_B: option_b.provider,
    }

    return (
        option_a_audio,
        option_b_audio,
        option_a_generation_id,
        option_b_generation_id,
        options_map,
    )

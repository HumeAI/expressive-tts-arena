"""
utils.py

This file contains utility functions that are shared across the project.
These functions provide reusable logic to simplify code in other modules.
"""

# Standard Library Imports
import base64
import json
import random
import time
from pathlib import Path
from typing import Tuple

# Local Application Imports
from src import constants
from src.config import AUDIO_DIR, logger
from src.custom_types import (
    ComparisonType,
    Option,
    OptionKey,
    OptionMap,
    TTSProviderName,
    VotingResults,
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
            f"Your character description is too short. Please enter at least "
            f"{constants.CHARACTER_DESCRIPTION_MIN_LENGTH} characters. "
            f"(Current length: {character_description_length})"
        )
    if character_description_length > constants.CHARACTER_DESCRIPTION_MAX_LENGTH:
        raise ValueError(
            f"Your character description is too long. Please limit it to "
            f"{constants.CHARACTER_DESCRIPTION_MAX_LENGTH} characters. "
            f"(Current length: {character_description_length})"
        )

    truncated_description = truncate_text(stripped_character_description)
    logger.debug(
        f"Character description length validation passed for character_description: {truncated_description}"
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


def save_base64_audio_to_file(base64_audio: str, filename: str) -> str:
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
    # Decode the base64-encoded audio into binary data.
    audio_bytes = base64.b64decode(base64_audio)

    # Construct the full absolute file path within the AUDIO_DIR directory using Path.
    file_path = Path(AUDIO_DIR) / filename

    # Delete all audio files older than 30 minutes before writing the new audio file.
    num_minutes = 30
    delete_files_older_than(AUDIO_DIR, num_minutes)

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


def choose_providers(
    text_modified: bool,
    character_description: str,
) -> Tuple[TTSProviderName, TTSProviderName]:
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

    return provider_a, provider_b


def create_shuffled_tts_options(option_a: Option, option_b: Option) -> OptionMap:
    """
    Create and shuffle TTS generation options.

    This function accepts two TTS generation options, shuffles them randomly,
    and returns an OptionMap with keys 'option_a' and 'option_b' corresponding
    to the shuffled options.

    Args:
        option_a (Option): The first TTS generation option.
        option_b (Option): The second TTS generation option.

    Returns:
        OptionMap: A mapping of shuffled TTS options, where each option includes
                   its provider, audio file path, and generation ID.
    """
    # Create a list of Option instances for the available providers.
    options = [option_a, option_b]

    # Randomly shuffle the list of options.
    random.shuffle(options)

    # Unpack the two options.
    shuffled_option_a, shuffled_option_b = options

    # Build a mapping from option constants to the corresponding providers.
    return {
        "option_a": {
            "provider": shuffled_option_a.provider,
            "generation_id": shuffled_option_a.generation_id,
            "audio_file_path": shuffled_option_a.audio,
        },
        "option_b": {
            "provider": shuffled_option_b.provider,
            "generation_id": shuffled_option_b.generation_id,
            "audio_file_path": shuffled_option_b.audio,
        },
    }


def determine_selected_option(
    selected_option_button: str,
) -> Tuple[OptionKey, OptionKey]:
    """
    Determines the selected option and the alternative option based on the user's selection.

    Args:
        selected_option_button (str): The option selected by the user, expected to be either
            constants.OPTION_A_KEY or constants.OPTION_B_KEY.

    Returns:
        tuple: A tuple (selected_option, other_option) where:
            - selected_option is the same as the selected_option.
            - other_option is the alternative option.
    """
    if selected_option_button == constants.SELECT_OPTION_A:
        selected_option, other_option = constants.OPTION_A_KEY, constants.OPTION_B_KEY
    elif selected_option_button == constants.SELECT_OPTION_B:
        selected_option, other_option = constants.OPTION_B_KEY, constants.OPTION_A_KEY
    else:
        raise ValueError(f"Invalid selected button: {selected_option_button}")

    return selected_option, other_option

def determine_comparison_type(
    provider_a: TTSProviderName,
    provider_b: TTSProviderName
) -> ComparisonType:
    """
    Determine the comparison type based on the given TTS provider names.

    If both providers are HUME_AI, the comparison type is HUME_TO_HUME.
    If either provider is ELEVENLABS, the comparison type is HUME_TO_ELEVENLABS.

    Args:
        provider_a (TTSProviderName): The first TTS provider.
        provider_b (TTSProviderName): The second TTS provider.

    Returns:
        ComparisonType: The determined comparison type.

    Raises:
        ValueError: If the combination of providers is not recognized.
    """
    if provider_a == constants.HUME_AI and provider_b == constants.HUME_AI:
        return constants.HUME_TO_HUME

    if constants.ELEVENLABS in (provider_a, provider_b):
        return constants.HUME_TO_ELEVENLABS

    raise ValueError(f"Invalid provider combination: {provider_a}, {provider_b}")


def submit_voting_results(
    option_map: OptionMap,
    selected_option: str,
    text_modified: bool,
    character_description: str,
    text: str,
) -> VotingResults:
    """
    Constructs the voting results dictionary from the provided inputs and logs it.

    Args:
        option_map (OptionMap): Mapping of comparison data and TTS options.
        selected_option (str): The option selected by the user.
        comparison_type (ComparisonType): The type of comparison between providers.
        text_modified (bool): Indicates whether the text was modified.
        character_description (str): Description of the voice/character.
        text (str): The text associated with the TTS generation.

    Returns:
        VotingResults: The constructed voting results dictionary.
    """
    provider_a: TTSProviderName = option_map[constants.OPTION_A_KEY]["provider"]
    provider_b: TTSProviderName = option_map[constants.OPTION_B_KEY]["provider"]
    comparison_type: ComparisonType = determine_comparison_type(provider_a, provider_b)

    voting_results: VotingResults = {
        "comparison_type": comparison_type,
        "winning_provider": option_map[selected_option]["provider"],
        "winning_option": selected_option,
        "option_a_provider": provider_a,
        "option_b_provider": provider_b,
        "option_a_generation_id": option_map[constants.OPTION_A_KEY]["generation_id"],
        "option_b_generation_id": option_map[constants.OPTION_B_KEY]["generation_id"],
        "voice_description": character_description,
        "text": text,
        "is_custom_text": text_modified,
    }
    # TODO: Currently logging the results until we hook the API for writing results to DB
    logger.info("Voting results:\n%s", json.dumps(voting_results, indent=4))
    return voting_results

"""
utils.py

This file contains utility functions that are shared across the project.
These functions provide reusable logic to simplify code in other modules.
"""

# Standard Library Imports
import base64
import json
import os
import time
from pathlib import Path
from typing import List, Tuple, cast

# Third-Party Library Imports
from sqlalchemy.ext.asyncio import AsyncSession

# Local Application Imports
from src.common import constants
from src.common.common_types import (
    ComparisonType,
    LeaderboardEntry,
    OptionKey,
    OptionMap,
    TTSProviderName,
    VotingResults,
)
from src.common.config import Config, logger
from src.database import (
    AsyncDBSessionMaker,
    create_vote,
    get_head_to_head_battle_stats,
    get_head_to_head_win_rate_stats,
    get_leaderboard_stats,
)


def __delete_files_older_than(directory: Path, minutes: int = 30) -> None:
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

    __delete_files_older_than(config.audio_dir, num_minutes)

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


def __determine_comparison_type(provider_a: TTSProviderName, provider_b: TTSProviderName) -> ComparisonType:
    """
    Determine the comparison type based on the given TTS provider names.

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

    providers = (provider_a, provider_b)

    if constants.HUME_AI in providers and constants.ELEVENLABS in providers:
        return constants.HUME_TO_ELEVENLABS

    if constants.HUME_AI in providers and constants.OPENAI in providers:
        return constants.HUME_TO_OPENAI

    if constants.ELEVENLABS in providers and constants.OPENAI in providers:
        return constants.OPENAI_TO_ELEVENLABS

    raise ValueError(f"Invalid provider combination: {provider_a}, {provider_b}")


def __log_voting_results(voting_results: VotingResults) -> None:
    """Log the full voting results."""

    logger.info("Voting results:\n%s", json.dumps(voting_results, indent=4))


async def __create_db_session(db_session_maker: AsyncDBSessionMaker) -> AsyncSession:
    """
    Creates a new database session using the provided session maker and checks if it's a dummy session.

    A dummy session might be used in development or testing environments where database operations
    should be simulated but not actually performed.

    Args:
        db_session_maker (AsyncDBSessionMaker): A callable that returns a new async database session.

    Returns:
        AsyncSession: A newly created database session that can be used for database operations.
    """
    session = db_session_maker()
    is_dummy_session = getattr(session, "is_dummy", False)

    if is_dummy_session:
        await session.close()
        return None

    return session


async def __persist_vote(db_session_maker: AsyncDBSessionMaker, voting_results: VotingResults) -> None:
    """
    Asynchronously persist a vote record in the database and handle potential failures.
    Designed to work safely in a background task context.

    Args:
        db_session_maker (AsyncDBSessionMaker): A callable that returns a new async database session.
        voting_results (VotingResults): A dictionary containing the details of the vote to persist.
        config (Config): The application configuration, used to determine environment-specific behavior.

    Returns:
        None
    """
    # Create session
    session = await __create_db_session(db_session_maker)
    __log_voting_results(voting_results)
    try:
        await create_vote(cast(AsyncSession, session), voting_results)
    except Exception as e:
        # Log the error with traceback
        logger.error(f"Failed to create vote record: {e}", exc_info=True)
    finally:
        # Always ensure the session is closed
        if session is not None:
            await session.close()


async def submit_voting_results(
    option_map: OptionMap,
    selected_option: OptionKey,
    text_modified: bool,
    character_description: str,
    text: str,
    db_session_maker: AsyncDBSessionMaker,
) -> None:
    """
    Asynchronously constructs the voting results dictionary and persists a new vote record.
    Designed to run as a background task, handling all exceptions internally.

    Args:
        option_map (OptionMap): Mapping of comparison data and TTS options.
        selected_option (OptionKey): The option selected by the user.
        text_modified (bool): Indicates whether the text was modified from the original generated text.
        character_description (str): Description of the voice/character used for TTS generation.
        text (str): The text that was synthesized into speech.
        db_session_maker (AsyncDBSessionMaker): Factory function for creating async database sessions.
        config (Config): Application configuration containing environment settings.

    Returns:
        None
    """
    try:
        provider_a: TTSProviderName = option_map[constants.OPTION_A_KEY]["provider"]
        provider_b: TTSProviderName = option_map[constants.OPTION_B_KEY]["provider"]

        comparison_type: ComparisonType = __determine_comparison_type(provider_a, provider_b)

        voting_results: VotingResults = {
            "comparison_type": comparison_type,
            "winning_provider": option_map[selected_option]["provider"],
            "winning_option": selected_option,
            "option_a_provider": provider_a,
            "option_b_provider": provider_b,
            "option_a_generation_id": option_map[constants.OPTION_A_KEY]["generation_id"],
            "option_b_generation_id": option_map[constants.OPTION_B_KEY]["generation_id"],
            "character_description": character_description,
            "text": text,
            "is_custom_text": text_modified,
        }

        await __persist_vote(db_session_maker, voting_results)

    # Catch exceptions at the top level of the background task to prevent unhandled exceptions in background tasks
    except Exception as e:
        logger.error(f"Background task error in submit_voting_results: {e}", exc_info=True)


async def get_leaderboard_data(
    db_session_maker: AsyncDBSessionMaker
) -> Tuple[List[List[str]], List[List[str]], List[List[str]]]:
    """
    Fetches and formats all leaderboard data from the voting results database.

    This function retrieves three different datasets:
    1. Provider rankings with overall performance metrics
    2. Head-to-head battle counts between providers
    3. Win rate percentages for each provider against others

    Args:
        db_session_maker (AsyncDBSessionMaker): Factory function for creating async database sessions.

    Returns:
        Tuple containing three datasets, each as List[List[str]]:
            - leaderboard_data: Provider rankings with performance metrics
            - battle_counts_data: Number of comparisons between each provider pair
            - win_rate_data: Win percentages in head-to-head matchups
    """
    # Create session
    session = await __create_db_session(db_session_maker)
    try:
        leaderboard_data_raw = await get_leaderboard_stats(cast(AsyncSession, session))
        battle_counts_data_raw = await get_head_to_head_battle_stats(cast(AsyncSession, session))
        win_rate_data_raw = await get_head_to_head_win_rate_stats(cast(AsyncSession, session))

        logger.debug("Fetched leaderboard data successfully.")

        leaderboard_data = __format_leaderboard_data(leaderboard_data_raw)
        battle_counts_data = __format_battle_counts_data(battle_counts_data_raw)
        win_rate_data = __format_win_rate_data(win_rate_data_raw)

        return leaderboard_data, battle_counts_data, win_rate_data
    except Exception as e:
        # Log the error with traceback
        logger.error(f"Failed to fetch leaderboard data: {e}", exc_info=True)
        return [[]], [[]], [[]]
    finally:
        # Always ensure the session is closed
        if session is not None:
            await session.close()

def __format_leaderboard_data(leaderboard_data_raw: List[LeaderboardEntry]) -> List[List[str]]:
    """
    Formats raw leaderboard data for display in the UI.

    Converts LeaderboardEntry objects into HTML-formatted strings with appropriate
    styling and links for provider and model information.

    Args:
        leaderboard_data_raw (List[LeaderboardEntry]): Raw leaderboard data from the database.

    Returns:
        List[List[str]]: Formatted HTML strings for each cell in the leaderboard table.
    """
    return [
        [
            f'<p style="text-align: center;">{row[0]}</p>',
            f"""<a href="{constants.TTS_PROVIDER_LINKS[row[1]]["provider_link"]}"
                target="_blank"
                class="provider-link"
            >{row[1]}</a>
            """,
            f"""<a href="{constants.TTS_PROVIDER_LINKS[row[1]]["model_link"]}"
                target="_blank"
                class="provider-link"
            >{row[2]}</a>
            """,
            f'<p style="text-align: center;">{row[3]}</p>',
            f'<p style="text-align: center;">{row[4]}</p>',
        ] for row in leaderboard_data_raw
    ]


def __format_battle_counts_data(battle_counts_data_raw: List[List[str]]) -> List[List[str]]:
    """
    Formats battle count data into a matrix format for the UI.

    Creates a provider-by-provider matrix showing the number of direct comparisons
    between each pair of providers. Diagonal cells show dashes as providers aren't
    compared against themselves.

    Args:
        battle_counts_data_raw (List[List[str]]): Raw battle count data from the database,
            where each inner list contains [comparison_type, count].

    Returns:
        List[List[str]]: HTML-formatted matrix of battle counts between providers.
    """
    battle_counts_dict = {item[0]: item[1] for item in battle_counts_data_raw}
    # Create canonical comparison keys based on your expected database formats
    comparison_keys = {
        ("Hume AI", "OpenAI"): "Hume AI - OpenAI",
        ("Hume AI", "ElevenLabs"): "Hume AI - ElevenLabs",
        ("OpenAI", "ElevenLabs"): "OpenAI - ElevenLabs"
    }
    return [
        [
            f'<p style="padding-left: 8px;"><strong>{row_provider}</strong></p>'
        ] + [
            f"""
            <p style="text-align: center;">
                {"-" if row_provider == col_provider
                    else battle_counts_dict.get(
                        comparison_keys.get((row_provider, col_provider)) or
                        comparison_keys.get((col_provider, row_provider), "unknown"),
                        "0"
                    )
                }
            </p>
            """ for col_provider in constants.TTS_PROVIDERS
        ]
        for row_provider in constants.TTS_PROVIDERS
    ]


def __format_win_rate_data(win_rate_data_raw: List[List[str]]) -> List[List[str]]:
    """
    Formats win rate data into a matrix format for the UI.

    Creates a provider-by-provider matrix showing the percentage of times the row
    provider won against the column provider. Diagonal cells show dashes as
    providers aren't compared against themselves.

    Args:
        win_rate_data_raw (List[List[str]]): Raw win rate data from the database,
            where each inner list contains [comparison_type, first_win_rate, second_win_rate].

    Returns:
        List[List[str]]: HTML-formatted matrix of win rates between providers.
    """
    # Create a clean lookup dictionary with provider pairs as keys
    win_rates = {}
    for comparison_type, first_win_rate, second_win_rate in win_rate_data_raw:
        provider1, provider2 = comparison_type.split(" - ")
        win_rates[(provider1, provider2)] = first_win_rate
        win_rates[(provider2, provider1)] = second_win_rate

    return [
        [
            f'<p style="padding-left: 8px;"><strong>{row_provider}</strong></p>'
        ] + [
            f"""
                <p style="text-align: center;">
                    {"-" if row_provider == col_provider else win_rates.get((row_provider, col_provider), "0%")}
                </p>
            """
            for col_provider in constants.TTS_PROVIDERS
        ]
        for row_provider in constants.TTS_PROVIDERS
    ]


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


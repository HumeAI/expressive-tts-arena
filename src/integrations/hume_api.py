"""
hume_api.py

This file defines the interaction with the Hume text-to-speech (TTS) API using the
Hume Python SDK. It includes functionality for API request handling and processing API responses.

Key Features:
- Encapsulates all logic related to the Hume TTS API.
- Implements retry logic for handling transient API errors.
- Handles received audio and processes it for playback on the web.
- Provides detailed logging for debugging and error tracking.
"""

# Standard Library Imports
import logging
import time
from dataclasses import dataclass, field
from typing import Tuple, Union

# Third-Party Library Imports
from hume import AsyncHumeClient
from hume.core.api_error import ApiError
from hume.tts import PostedUtterance
from hume.tts.types import ReturnGeneration, ReturnTts
from hume.tts.types.format import Format, FormatMp3
from tenacity import after_log, before_log, retry, retry_if_exception, stop_after_attempt, wait_exponential

# Local Application Imports
from src.config import Config, logger
from src.constants import CLIENT_ERROR_CODE, SERVER_ERROR_CODE
from src.utils import save_base64_audio_to_file, validate_env_var


@dataclass(frozen=True)
class HumeConfig:
    """Immutable configuration for interacting with the Hume TTS API."""

    api_key: str = field(init=False)
    file_format: Format = field(default_factory=FormatMp3)
    request_timeout: float = 40.0

    def __post_init__(self) -> None:
        """Validate required attributes and set computed fields."""
        if not self.file_format:
            raise ValueError("Hume TTS file format is not set.")

        computed_api_key = validate_env_var("HUME_API_KEY")
        object.__setattr__(self, "api_key", computed_api_key)


class HumeError(Exception):
    """Custom exception for errors related to the Hume TTS API."""

    def __init__(self, message: str, original_exception: Union[Exception, None] = None):
        super().__init__(message)
        self.original_exception = original_exception
        self.message = message


class UnretryableHumeError(HumeError):
    """Custom exception for errors related to the Hume TTS API that should not be retried."""

    def __init__(self, message: str, original_exception: Union[Exception, None] = None):
        super().__init__(message, original_exception)
        self.original_exception = original_exception
        self.message = message


@retry(
    retry=retry_if_exception(lambda e: not isinstance(e, UnretryableHumeError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=5),
    before=before_log(logger, logging.DEBUG),
    after=after_log(logger, logging.DEBUG),
    reraise=True,
)
async def text_to_speech_with_hume(
    character_description: str,
    text: str,
    config: Config,
) -> Tuple[str, str]:
    """
    Asynchronously synthesizes speech using the Hume TTS API, processes audio data, and writes audio to a file.

    This function uses the Hume Python SDK to send a request to the Hume TTS API with a character description
    and text to be converted to speech. It extracts the base64-encoded audio and generation ID from the response,
    saves the audio as an MP3 file, and returns the relevant details.

    Args:
        character_description (str): Description used for voice synthesis.
        text (str): Text to be converted to speech.
        config (Config): Application configuration containing Hume API settings.

    Returns:
        Tuple[str, str]: A tuple containing:
            - generation_id (str): Unique identifier for the generated audio.
            - audio_file_path (str): Path to the saved audio file.

    Raises:
        HumeError: For errors communicating with the Hume API.
        UnretryableHumeError: For client-side HTTP errors (status code 4xx).
    """
    logger.debug(
        "Processing TTS with Hume. "
        f"Character description length: {len(character_description)}. "
        f"Text length: {len(text)}."
    )

    hume_config = config.hume_config

    start_time = time.time()
    try:
        hume_client = AsyncHumeClient(
            api_key=hume_config.api_key,
            timeout=hume_config.request_timeout
        )

        utterance = PostedUtterance(
            text=text,
            description=character_description or None
        )

        response: ReturnTts = await hume_client.tts.synthesize_json(
            utterances=[utterance],
            format=hume_config.file_format,
        )

        elapsed_time = time.time() - start_time
        logger.info(f"Hume API request completed in {elapsed_time:.2f} seconds")

        generations = response.generations
        if not generations:
            msg = "No generations returned by Hume API."
            logger.error(msg)
            raise HumeError(msg)

        generation_a = generations[0]
        generation_a_id, audio_a_path = _parse_hume_tts_generation(generation_a, config)

        return (generation_a_id, audio_a_path)

    except ApiError as e:
        elapsed_time = time.time() - start_time
        logger.error(f"Hume API request failed after {elapsed_time:.2f} seconds: {e!s}")
        clean_message = _extract_hume_api_error_message(e)
        logger.error(f"Full Hume API error: {e!s}")

        if (
            hasattr(e, 'status_code')
            and e.status_code is not None
            and CLIENT_ERROR_CODE <= e.status_code < SERVER_ERROR_CODE
        ):
            raise UnretryableHumeError(message=clean_message, original_exception=e) from e

        raise HumeError(message=clean_message, original_exception=e) from e

    except Exception as e:
        error_type = type(e).__name__
        error_message = str(e) if str(e) else f"An error of type {error_type} occurred"
        logger.error("Error during Hume API call: %s - %s", error_type, error_message)
        raise HumeError(message=error_message, original_exception=e) from e


def _parse_hume_tts_generation(generation: ReturnGeneration, config: Config) -> Tuple[str, str]:
    """
    Parses a Hume TTS generation response and saves the decoded audio as an MP3 file.

    Args:
        generation (ReturnGeneration): TTS generation response containing generation_id and audio.
        config (Config): Application configuration for saving the audio file.

    Returns:
        Tuple[str, str]: (generation_id, audio_path)

    Raises:
        KeyError: If expected attributes are missing.
        Exception: Propagates exceptions from saving the audio file.
    """
    if not generation.generation_id:
        raise KeyError("The generation is missing the generation_id.")

    if not generation.audio:
        raise KeyError("The generation is missing the audio data.")

    filename = f"{generation.generation_id}.mp3"
    audio_file_path = save_base64_audio_to_file(generation.audio, filename, config)
    return generation.generation_id, audio_file_path


def _extract_hume_api_error_message(e: ApiError) -> str:
    """
    Extracts a clean, user-friendly error message from a Hume API error response.

    Args:
        e (ApiError): The Hume API error exception containing response information.

    Returns:
        str: A clean, user-friendly error message suitable for display to end users.
    """
    clean_message = "An unknown error has occurred. Please try again later."

    if hasattr(e, 'body') and isinstance(e.body, dict) and 'message' in e.body:
            clean_message = e.body['message']

    return clean_message

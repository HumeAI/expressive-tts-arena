"""
hume_api.py

This file defines the interaction with the Hume text-to-speech (TTS) API.
It includes functionality for API request handling and processing API responses.

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
from typing import Any, Dict, Literal, Tuple, Union

# Third-Party Library Imports
import httpx
from tenacity import after_log, before_log, retry, retry_if_exception, stop_after_attempt, wait_exponential

# Local Application Imports
from src.config import Config, logger
from src.constants import CLIENT_ERROR_CODE, SERVER_ERROR_CODE
from src.utils import save_base64_audio_to_file, validate_env_var

HumeSupportedFileFormat = Literal["mp3", "pcm", "wav"]
"""Supported audio file formats for the Hume TTS API"""


@dataclass(frozen=True)
class HumeConfig:
    """Immutable configuration for interacting with the Hume TTS API."""

    api_key: str = field(init=False)
    headers: Dict[str, str] = field(init=False)
    url: str = "https://api.hume.ai/v0/tts/octave"
    file_format: HumeSupportedFileFormat = "mp3"
    request_timeout: float = 60.0

    def __post_init__(self) -> None:
        # Validate required attributes.
        if not self.url:
            raise ValueError("Hume TTS endpoint URL is not set.")
        if not self.file_format:
            raise ValueError("Hume TTS file format is not set.")

        computed_api_key = validate_env_var("HUME_API_KEY")
        object.__setattr__(self, "api_key", computed_api_key)
        computed_headers = {
            "X-Hume-Api-Key": f"{computed_api_key}",
            "Content-Type": "application/json",
        }
        object.__setattr__(self, "headers", computed_headers)


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
    num_generations: int,
    config: Config,
) -> Union[Tuple[str, str], Tuple[str, str, str, str]]:
    """
    Asynchronously synthesizes speech using the Hume TTS API, processes audio data, and writes audio to a file.

    This function sends a POST request to the Hume TTS API with a character description and text to be converted to
    speech. Depending on the specified number of generations (1 or 2), the API returns one or two generations.
    For each generation, the function extracts the base64-encoded audio and generation ID, saves the audio as an MP3
    file, and returns the relevant details.

    Args:
        character_description (str): Description used for voice synthesis.
        text (str): Text to be converted to speech.
        num_generations (int): Number of audio generations to request (1 or 2).
        config (Config): Application configuration containing Hume API settings.

    Returns:
        Union[Tuple[str, str], Tuple[str, str, str, str]]:
            - If num_generations == 1: (generation_a_id, audio_a_path).
            - If num_generations == 2: (generation_a_id, audio_a_path, generation_b_id, audio_b_path).

    Raises:
        ValueError: If num_generations is not 1 or 2.
        HumeError: For errors communicating with the Hume API.
        UnretryableHumeError: For client-side HTTP errors (status code 4xx).
    """
    logger.debug(
        "Processing TTS with Hume. "
        f"Character description length: {len(character_description)}. "
        f"Text length: {len(text)}."
    )

    if num_generations < 1 or num_generations > 2:
        raise ValueError("Invalid number of generations specified. Must be 1 or 2.")

    hume_config = config.hume_config
    request_body = {
        "utterances": [{"text": text, "description": character_description or None}],
        "format": {"type": hume_config.file_format},
        "num_generations": num_generations,
    }

    start_time = time.time()
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url=hume_config.url,
                headers=hume_config.headers,
                json=request_body,
                timeout=hume_config.request_timeout,
            )
            elapsed_time = time.time() - start_time
            logger.info(f"Hume API request completed in {elapsed_time:.2f} seconds")
            response.raise_for_status()
            response_data = response.json()

        generations = response_data.get("generations")
        if not generations:
            msg = "No generations returned by Hume API."
            logger.error(msg)
            raise HumeError(msg)

        generation_a = generations[0]
        generation_a_id, audio_a_path = _parse_hume_tts_generation(generation_a, config)

        if num_generations == 1:
            return (generation_a_id, audio_a_path)

        generation_b = generations[1]
        generation_b_id, audio_b_path = _parse_hume_tts_generation(generation_b, config)
        return (generation_a_id, audio_a_path, generation_b_id, audio_b_path)

    except (httpx.ReadTimeout, httpx.ConnectTimeout, httpx.ConnectError) as e:
        logger.error(f"Hume API request failed after {elapsed_time:.2f} seconds: {e!s}")
        raise HumeError(
            message=f"Connection to Hume API failed: {e!s}. Please try again later.",
            original_exception=e,
        ) from e

    except httpx.HTTPStatusError as e:
        if e.response is not None and CLIENT_ERROR_CODE <= e.response.status_code < SERVER_ERROR_CODE:
            error_message = f"HTTP Error {e.response.status_code}: {e.response.text}"
            logger.error(error_message)
            raise UnretryableHumeError(
                message=error_message,
                original_exception=e,
            ) from e
        error_message = f"HTTP Error {e.response.status_code if e.response else 'unknown'}"
        logger.error(error_message)
        raise HumeError(
            message=error_message,
            original_exception=e,
        ) from e

    except Exception as e:
        error_type = type(e).__name__
        error_message = str(e) if str(e) else f"An error of type {error_type} occurred"
        logger.error("Error during Hume API call: %s - %s", error_type, error_message)
        raise HumeError(
            message=error_message,
            original_exception=e,
        ) from e

def _parse_hume_tts_generation(generation: Dict[str, Any], config: Config) -> Tuple[str, str]:
    """
    Parses a Hume TTS generation response and saves the decoded audio as an MP3 file.

    Args:
        generation (Dict[str, Any]): TTS generation response containing 'generation_id' and 'audio'.
        config (Config): Application configuration for saving the audio file.

    Returns:
        Tuple[str, str]: (generation_id, audio_path)

    Raises:
        KeyError: If expected keys are missing.
        Exception: Propagates exceptions from saving the audio file.
    """
    generation_id = generation.get("generation_id")
    if generation_id is None:
        raise KeyError("The generation dictionary is missing the 'generation_id' key.")

    base64_audio = generation.get("audio")
    if base64_audio is None:
        raise KeyError("The generation dictionary is missing the 'audio' key.")

    filename = f"{generation_id}.mp3"
    audio_file_path = save_base64_audio_to_file(base64_audio, filename, config)
    return generation_id, audio_file_path

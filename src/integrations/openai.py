# Standard Library Imports
import logging
import random
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Tuple, Union

# Third-Party Library Imports
from openai import APIError, AsyncOpenAI
from tenacity import after_log, before_log, retry, retry_if_exception, stop_after_attempt, wait_fixed

# Local Application Imports
from src.common import Config, logger
from src.common.constants import CLIENT_ERROR_CODE, GENERIC_API_ERROR_MESSAGE, RATE_LIMIT_ERROR_CODE, SERVER_ERROR_CODE
from src.common.utils import validate_env_var


@dataclass(frozen=True)
class OpenAIConfig:
    """Immutable configuration for interacting with the OpenAI TTS API."""

    api_key: str = field(init=False)
    model: str = "gpt-4o-mini-tts"
    response_format: Literal['mp3', 'opus', 'aac', 'flac', 'wav', 'pcm'] = "mp3"

    def __post_init__(self) -> None:
        """Validate required attributes and set computed fields."""

        computed_api_key = validate_env_var("OPENAI_API_KEY")
        object.__setattr__(self, "api_key", computed_api_key)

    @property
    def client(self) -> AsyncOpenAI:
        """
        Lazy initialization of the asynchronous OpenAI client.

        Returns:
            AsyncOpenAI: Configured async client instance.
        """
        return AsyncOpenAI(api_key=self.api_key)

    @staticmethod
    def select_random_base_voice() -> str:
        """
        Randomly selects one of OpenAI's base voice options for TTS.

        OpenAI's Python SDK doesn't export a type for their base voice names,
        so we use a hardcoded list of the available voice options.

        Returns:
            str: A randomly selected OpenAI base voice name (e.g., 'alloy', 'nova', etc.)
        """
        openai_base_voices = ["alloy", "ash", "coral", "echo", "fable", "onyx", "nova", "sage", "shimmer"]
        return random.choice(openai_base_voices)

class OpenAIError(Exception):
    """Custom exception for errors related to the OpenAI TTS API."""

    def __init__(self, message: str, original_exception: Union[Exception, None] = None):
        super().__init__(message)
        self.original_exception = original_exception
        self.message = message

class UnretryableOpenAIError(OpenAIError):
    """Custom exception for errors related to the OpenAI TTS API that should not be retried."""

    def __init__(self, message: str, original_exception: Union[Exception, None] = None):
        super().__init__(message, original_exception)
        self.original_exception = original_exception
        self.message = message

@retry(
    retry=retry_if_exception(lambda e: not isinstance(e, UnretryableOpenAIError)),
    stop=stop_after_attempt(2),
    wait=wait_fixed(2),
    before=before_log(logger, logging.DEBUG),
    after=after_log(logger, logging.DEBUG),
    reraise=True,
)
async def text_to_speech_with_openai(
    character_description: str,
    text: str,
    config: Config,
) -> Tuple[None, str]:
    """
    Asynchronously synthesizes speech using the OpenAI TTS API, processes audio data, and writes audio to a file.

    This function uses the OpenAI Python SDK to send a request to the OpenAI TTS API with a character description
    and text to be converted to speech. It extracts the base64-encoded audio and generation ID from the response,
    saves the audio as an MP3 file, and returns the relevant details.

    Args:
        character_description (str): Description used for voice synthesis.
        text (str): Text to be converted to speech.
        config (Config): Application configuration containing OpenAI API settings.

    Returns:
        Tuple[str, str]: A tuple containing:
            - generation_id (str): Unique identifier for the generated audio.
            - audio_file_path (str): Path to the saved audio file.

    Raises:
        OpenAIError: For errors communicating with the OpenAI API.
        UnretryableOpenAIError: For client-side HTTP errors (status code 4xx).
    """
    logger.debug(f"Synthesizing speech with OpenAI. Text length: {len(text)} characters.")
    openai_config = config.openai_config
    client = openai_config.client
    start_time = time.time()
    try:
        voice = openai_config.select_random_base_voice()
        async with client.audio.speech.with_streaming_response.create(
            model=openai_config.model,
            input=text,
            instructions=character_description,
            response_format=openai_config.response_format,
            voice=voice, # OpenAI requires a base voice to be specified
        ) as response:
            elapsed_time = time.time() - start_time
            logger.info(f"OpenAI API request completed in {elapsed_time:.2f} seconds.")

            filename = f"openai_{voice}_{start_time}"
            audio_file_path = Path(config.audio_dir) / filename
            await response.stream_to_file(audio_file_path)
            relative_audio_file_path = audio_file_path.relative_to(Path.cwd())

            return None, str(relative_audio_file_path)

    except APIError as e:
        elapsed_time = time.time() - start_time
        logger.error(f"OpenAI API request failed after {elapsed_time:.2f} seconds: {e!s}")
        logger.error(f"Full OpenAI API error: {e!s}")
        clean_message = __extract_openai_error_message(e)

        if hasattr(e, 'status_code') and  e.status_code is not None:
            if e.status_code == RATE_LIMIT_ERROR_CODE:
                raise OpenAIError(message=clean_message, original_exception=e) from e
            if CLIENT_ERROR_CODE <= e.status_code < SERVER_ERROR_CODE:
                raise UnretryableOpenAIError(message=clean_message, original_exception=e) from e

        raise OpenAIError(message=clean_message, original_exception=e) from e

    except Exception as e:
        error_type = type(e).__name__
        error_message = str(e) if str(e) else f"An error of type {error_type} occurred"
        logger.error("Error during OpenAI API call: %s - %s", error_type, error_message)
        clean_message = GENERIC_API_ERROR_MESSAGE

        raise OpenAIError(message=clean_message, original_exception=e) from e

def __extract_openai_error_message(e: APIError) -> str:
    """
    Extracts a clean, user-friendly error message from an OpenAI API error response.

    Args:
        e (APIError): The OpenAI API error exception containing response information.

    Returns:
        str: A clean, user-friendly error message suitable for display to end users.
    """
    clean_message = GENERIC_API_ERROR_MESSAGE

    if hasattr(e, 'body') and isinstance(e.body, dict):
        error_body = e.body
        if (
            'error' in error_body
            and isinstance(error_body['error'], dict)
            and 'message' in error_body['error']
        ):
            clean_message = error_body['error']['message']

    return clean_message

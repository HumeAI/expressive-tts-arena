# Standard Library Imports
import logging
import random
import time
from dataclasses import dataclass, field
from typing import Optional, Tuple

# Third-Party Library Imports
from elevenlabs import AsyncElevenLabs, TextToVoiceCreatePreviewsRequestOutputFormat
from elevenlabs.core import ApiError
from tenacity import after_log, before_log, retry, retry_if_exception, stop_after_attempt, wait_fixed

# Local Application Imports
from src.common import Config, logger, save_base64_audio_to_file, validate_env_var
from src.common.constants import CLIENT_ERROR_CODE, GENERIC_API_ERROR_MESSAGE, RATE_LIMIT_ERROR_CODE, SERVER_ERROR_CODE


@dataclass(frozen=True)
class ElevenLabsConfig:
    """Immutable configuration for interacting with the ElevenLabs TTS API."""

    api_key: str = field(init=False)
    output_format: TextToVoiceCreatePreviewsRequestOutputFormat = "mp3_44100_128"

    def __post_init__(self):
        # Validate required attributes.
        if not self.output_format:
            raise ValueError("ElevenLabs TTS API output format is not set.")

        computed_key = validate_env_var("ELEVENLABS_API_KEY")
        object.__setattr__(self, "api_key", computed_key)

    @property
    def client(self) -> AsyncElevenLabs:
        """
        Lazy initialization of the asynchronous ElevenLabs client.

        Returns:
            AsyncElevenLabs: Configured async client instance.
        """
        return AsyncElevenLabs(api_key=self.api_key)

class ElevenLabsError(Exception):
    """Custom exception for errors related to the ElevenLabs TTS API."""

    def __init__(self, message: str, original_exception: Optional[Exception] = None):
        super().__init__(message)
        self.original_exception = original_exception
        self.message = message

class UnretryableElevenLabsError(ElevenLabsError):
    """Custom exception for errors related to the ElevenLabs TTS API that should not be retried."""

    def __init__(self, message: str, original_exception: Optional[Exception] = None):
        super().__init__(message, original_exception)
        self.original_exception = original_exception
        self.message = message

@retry(
    retry=retry_if_exception(lambda e: not isinstance(e, UnretryableElevenLabsError)),
    stop=stop_after_attempt(2),
    wait=wait_fixed(2),
    before=before_log(logger, logging.DEBUG),
    after=after_log(logger, logging.DEBUG),
    reraise=True,
)
async def text_to_speech_with_elevenlabs(
    character_description: str, text: str, config: Config
) -> Tuple[None, str]:
    """
    Asynchronously synthesizes speech using the ElevenLabs TTS API, processes the audio data, and writes it to a file.

    Args:
        character_description (str): The character description used for voice synthesis.
        text (str): The text to be synthesized into speech.
        config (Config): Application configuration containing ElevenLabs API settings.

    Returns:
        Tuple[None, str]: A tuple containing:
            - generation_id (None): A placeholder (no generation ID is returned).
            - file_path (str): The relative file path to the saved audio file.

    Raises:
        ElevenLabsError: If there is an error communicating with the ElevenLabs API or processing the response.
    """
    logger.debug(f"Synthesizing speech with ElevenLabs. Text length: {len(text)} characters.")
    elevenlabs_config = config.elevenlabs_config
    client = elevenlabs_config.client
    start_time = time.time()
    try:
        response = await client.text_to_voice.create_previews(
            voice_description=character_description,
            text=text,
            output_format=elevenlabs_config.output_format,
        )

        elapsed_time = time.time() - start_time
        logger.info(f"Elevenlabs API request completed in {elapsed_time:.2f} seconds.")

        previews = response.previews
        if not previews:
            raise ElevenLabsError(message="No previews returned by ElevenLabs API.")

        preview = random.choice(previews)
        generated_voice_id = preview.generated_voice_id
        base64_audio = preview.audio_base_64
        filename = f"{generated_voice_id}.mp3"
        audio_file_path = save_base64_audio_to_file(base64_audio, filename, config)

        return None, audio_file_path

    except ApiError as e:
        logger.error(f"ElevenLabs API request failed: {e!s}")
        clean_message = __extract_elevenlabs_error_message(e)

        if hasattr(e, 'status_code') and  e.status_code is not None:
            if e.status_code == RATE_LIMIT_ERROR_CODE:
                raise ElevenLabsError(message=clean_message, original_exception=e) from e
            if CLIENT_ERROR_CODE <= e.status_code < SERVER_ERROR_CODE:
                raise UnretryableElevenLabsError(message=clean_message, original_exception=e) from e

        raise ElevenLabsError(message=clean_message, original_exception=e) from e

    except Exception as e:
        error_type = type(e).__name__
        error_message = str(e) if str(e) else f"An error of type {error_type} occurred"
        logger.error(f"Error during ElevenLabs API call: {error_type} - {error_message}")
        clean_message = GENERIC_API_ERROR_MESSAGE

        raise ElevenLabsError(message=error_message, original_exception=e) from e

def __extract_elevenlabs_error_message(e: ApiError) -> str:
    """
    Extracts a clean, user-friendly error message from an ElevenLabs API error response.

    Args:
        e (ApiError): The ElevenLabs API error exception containing response information.

    Returns:
        str: A clean, user-friendly error message suitable for display to end users.
    """
    clean_message = GENERIC_API_ERROR_MESSAGE

    if (
        hasattr(e, 'body') and e.body
        and isinstance(e.body, dict)
        and 'detail' in e.body
        and isinstance(e.body['detail'], dict)
    ):
        detail = e.body['detail']
        if 'message' in detail:
            clean_message = detail['message']

    return clean_message

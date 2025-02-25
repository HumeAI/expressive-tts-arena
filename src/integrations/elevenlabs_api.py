"""
elevenlabs_api.py

This file defines the interaction with the ElevenLabs text-to-speech (TTS) API using the
ElevenLabs Python SDK. It includes functionality for API request handling and processing API responses.

Key Features:
- Encapsulates all logic related to the ElevenLabs TTS API.
- Implements retry logic using Tenacity for handling transient API errors.
- Handles received audio and processes it for playback on the web.
- Provides detailed logging for debugging and error tracking.
- Utilizes robust error handling (EAFP) to validate API responses.
"""

# Standard Library Imports
import logging
import random
from dataclasses import dataclass, field
from typing import Optional, Tuple

# Third-Party Library Imports
from elevenlabs import AsyncElevenLabs, TextToVoiceCreatePreviewsRequestOutputFormat
from elevenlabs.core import ApiError
from tenacity import after_log, before_log, retry, retry_if_exception, stop_after_attempt, wait_fixed

# Local Application Imports
from src.config import Config, logger
from src.constants import CLIENT_ERROR_CODE, SERVER_ERROR_CODE
from src.utils import save_base64_audio_to_file, validate_env_var


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
    stop=stop_after_attempt(3),
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

    try:
        # Synthesize speech using the ElevenLabs SDK
        response = await elevenlabs_config.client.text_to_voice.create_previews(
            voice_description=character_description,
            text=text,
            output_format=elevenlabs_config.output_format,
        )

        previews = response.previews
        if not previews:
            msg = "No previews returned by ElevenLabs API."
            logger.error(msg)
            raise ElevenLabsError(message=msg)

        # Extract the base64 encoded audio and generated voice ID from the preview
        preview = random.choice(previews)
        generated_voice_id = preview.generated_voice_id
        base64_audio = preview.audio_base_64
        filename = f"{generated_voice_id}.mp3"

        # Write audio to file and return the relative path
        audio_file_path = save_base64_audio_to_file(base64_audio, filename, config)

        return None, audio_file_path

    except Exception as e:
        if (
            isinstance(e, ApiError)
            and e.status_code is not None
            and CLIENT_ERROR_CODE <= e.status_code < SERVER_ERROR_CODE
        ):
            raise UnretryableElevenLabsError(
                message=f"{e.body['detail']['message']}",
                original_exception=e,
            ) from e

        raise ElevenLabsError(
            message=f"{e}",
            original_exception=e,
        ) from e

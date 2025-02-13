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

Classes:
- ElevenLabsConfig: Immutable configuration for interacting with ElevenLabs' TTS API.
- ElevenLabsError: Custom exception for ElevenLabs API-related errors.

Functions:
- text_to_speech_with_elevenlabs: Synthesizes speech from text using ElevenLabs' TTS API.
"""

# Standard Library Imports
import logging
import random
from dataclasses import dataclass
from typing import Optional, Tuple

# Third-Party Library Imports
from elevenlabs import ElevenLabs, TextToVoiceCreatePreviewsRequestOutputFormat
from elevenlabs.core import ApiError
from tenacity import after_log, before_log, retry, stop_after_attempt, wait_fixed

# Local Application Imports
from src.config import Config, logger
from src.constants import CLIENT_ERROR_CODE, SERVER_ERROR_CODE
from src.utils import save_base64_audio_to_file, validate_env_var


@dataclass(frozen=True)
class ElevenLabsConfig:
    """Immutable configuration for interacting with the ElevenLabs TTS API."""

    api_key: Optional[str] = None
    output_format: TextToVoiceCreatePreviewsRequestOutputFormat = "mp3_44100_128"

    def __post_init__(self):
        # Validate that required attributes are set
        if not self.api_key:
            api_key = validate_env_var("ELEVENLABS_API_KEY")
            object.__setattr__(self, "api_key", api_key)

    @property
    def client(self) -> ElevenLabs:
        """
        Lazy initialization of the ElevenLabs client.

        Returns:
            ElevenLabs: Configured client instance.
        """
        return ElevenLabs(api_key=self.api_key)


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


@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(2),
    before=before_log(logger, logging.DEBUG),
    after=after_log(logger, logging.DEBUG),
    reraise=True,
)
def text_to_speech_with_elevenlabs(character_description: str, text: str, config: Config) -> Tuple[None, str]:
    """
    Synthesizes text to speech using the ElevenLabs TTS API, processes the audio data, and writes it to a file.

    Args:
        character_description (str): The character description used as the voice description.
        text (str): The text to be synthesized into speech.

    Returns:
        Tuple[None, str]: A tuple containing:
            - generation_id (None): We do not record the generation ID for ElevenLabs, but return None for uniformity
                                    across TTS integrations
            - file_path (str): The relative file path to the audio file where the synthesized speech was saved.

    Raises:
        ElevenLabsError: If there is an error communicating with the ElevenLabs API or processing the response.
    """
    logger.debug(f"Synthesizing speech with ElevenLabs. Text length: {len(text)} characters.")

    elevenlabs_config = config.elevenlabs_config

    try:
        # Synthesize speech using the ElevenLabs SDK
        response = elevenlabs_config.client.text_to_voice.create_previews(
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
        audio_file_path = save_base64_audio_to_file(base64_audio, filename, config)

        # Write audio to file and return the relative path
        return None, audio_file_path

    except Exception as e:
        if isinstance(e, ApiError) and e.status_code >= CLIENT_ERROR_CODE and e.status_code < SERVER_ERROR_CODE:
            raise UnretryableElevenLabsError(
                message=f"{e.body['detail']['message']}",
                original_exception=e,
            ) from e

        raise ElevenLabsError(
            message=f"{e}",
            original_exception=e,
        ) from e

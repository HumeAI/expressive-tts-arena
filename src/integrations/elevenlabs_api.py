"""
elevenlabs_api.py

This file defines the interaction with the ElevenLabs TTS API using the ElevenLabs Python SDK.
It includes functionality for API request handling and processing API responses.

Key Features:
- Encapsulates all logic related to the ElevenLabs TTS API.
- Implements retry logic for handling transient API errors.
- Handles received audio and processes it for playback on the web.
- Provides detailed logging for debugging and error tracking.

Classes:
- ElevenLabsException: Custom exception for TTS API-related errors.
- ElevenLabsConfig: Immutable configuration for interacting with the TTS API.

Functions:
- text_to_speech_with_elevenlabs: Converts text to speech using the ElevenLabs TTS API.
"""

# Standard Library Imports
from dataclasses import dataclass
import logging
from typing import Optional
# Third-Party Library Imports
from elevenlabs import ElevenLabs
from tenacity import retry, stop_after_attempt, wait_fixed, before_log, after_log
# Local Application Imports
from src.config import logger
from src.utils import validate_env_var, truncate_text


@dataclass(frozen=True)
class ElevenLabsConfig:
    """Immutable configuration for interacting with the ElevenLabs TTS API."""
    api_key: str = validate_env_var("ELEVENLABS_API_KEY")
    voice_id: str = "pNInz6obpgDQGcFmaJgB" # Adam (popular ElevenLabs pre-made voice)
    model_id: str = "eleven_multilingual_v2" # ElevenLab's most emotionally expressive model
    output_format: str = "mp3_44100_128" # Output format of the generated audio.

    def __post_init__(self):
        # Validate that required attributes are set
        if not self.api_key:
            raise ValueError("ElevenLabs API key is not set.")
        if not self.voice_id:
            raise ValueError("ElevenLabs Voice ID is not set.")
        if not self.model_id:
            raise ValueError("ElevenLabs Model ID is not set.")

    @property
    def client(self) -> ElevenLabs:
        """
        Lazy initialization of the ElevenLabs client.

        Returns:
            ElevenLabs: Configured client instance.
        """
        return ElevenLabs(api_key=self.api_key)


class ElevenLabsException(Exception):
    """Custom exception for errors related to the ElevenLabs TTS API."""
    def __init__(self, message: str, original_exception: Optional[Exception] = None):
        super().__init__(message)
        self.original_exception = original_exception


# Initialize the ElevenLabs client
elevenlabs_config = ElevenLabsConfig()


@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(2),
    before=before_log(logger, logging.DEBUG),
    after=after_log(logger, logging.DEBUG),
)
def text_to_speech_with_elevenlabs(text: str) -> bytes:
    """
    Converts text to speech using the ElevenLabs TTS API.

    Args:
        text (str): The text to be converted to speech.

    Returns:
        bytes: The raw binary audio data for playback.

    Raises:
        ElevenLabsException: If there is an error communicating with the ElevenLabs API or processing the response.
    """
    logger.debug(f"Generated text for TTS: {truncate_text(text)}")
    logger.debug(f"Using Voice ID: {elevenlabs_config.voice_id}")
    logger.debug(f"Using Model ID: {elevenlabs_config.model_id}")
    logger.debug(f"Using Output Format: {elevenlabs_config.output_format}")

    try:
        # Generate audio using the ElevenLabs SDK
        audio_iterator = elevenlabs_config.client.text_to_speech.convert(
            text=text,
            voice_id=elevenlabs_config.voice_id,
            model_id=elevenlabs_config.model_id,
            output_format=elevenlabs_config.output_format,
        )

       # Ensure the response is an iterator
        if not hasattr(audio_iterator, "__iter__") or not hasattr(audio_iterator, "__next__"):
            logger.error(f"Invalid audio iterator response: {audio_iterator}")
            raise ElevenLabsException("Invalid audio iterator received from ElevenLabs API.")

        # Combine chunks into a single bytes object
        audio = b"".join(chunk for chunk in audio_iterator)

        # Validate audio
        if not audio:
            logger.error("No audio data received from ElevenLabs API.")
            raise ElevenLabsException("Empty audio data received from ElevenLabs API.")

        logger.debug(f"Received binary audio data: {len(audio)} bytes")
        return audio

    except Exception as e:
        logger.exception(
            f"Error generating text-to-speech with ElevenLabs: {e}. "
            f"Text: {truncate_text(text)}, Voice ID: {elevenlabs_config.voice_id}"
        )
        raise ElevenLabsException(
            message=f"Failed to generate audio with ElevenLabs: {e}",
            original_exception=e,
        )
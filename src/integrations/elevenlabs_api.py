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
- ElevenLabsConfig: Immutable configuration for interacting with the TTS API.
- ElevenLabsError: Custom exception for TTS API-related errors.

Functions:
- text_to_speech_with_elevenlabs: Converts text to speech using the ElevenLabs TTS API.
"""

# Standard Library Imports
from dataclasses import dataclass
import logging
import random
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
    api_key: str = validate_env_var('ELEVENLABS_API_KEY')
    model_id: str = 'eleven_multilingual_v2' # ElevenLab's most emotionally expressive model
    output_format: str = 'mp3_44100_128' # Output format of the generated audio.
    top_voices: list[str] = (
        'pNInz6obpgDQGcFmaJgB',  # Adam
        'ErXwobaYiN019PkySvjV',  # Antoni
        '21m00Tcm4TlvDq8ikWAM',  # Rachel
        'XrExE9yKIg1WjnnlVkGX',  # Matilda
    )

    def __post_init__(self):
        # Validate that required attributes are set
        if not self.api_key:
            raise ValueError('ElevenLabs API key is not set.')
        if not self.model_id:
            raise ValueError('ElevenLabs Model ID is not set.')
        if not self.output_format:
            raise ValueError('ElevenLabs Output Format is not set.')
        if not self.top_voices:
            raise ValueError('ElevenLabs Top Voices are not set.')
    
    @property
    def client(self) -> ElevenLabs:
        """
        Lazy initialization of the ElevenLabs client.

        Returns:
            ElevenLabs: Configured client instance.
        """
        return ElevenLabs(api_key=self.api_key)

    @property
    def random_voice_id(self) -> str:
        """
        Randomly selects a voice ID from the top default voices, ensuring different voices across calls.
        """
        return random.choice(self.top_voices)


class ElevenLabsError(Exception):
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
    reraise=True
)
def text_to_speech_with_elevenlabs(text: str) -> bytes:
    """
    Converts text to speech using the ElevenLabs TTS API.

    Args:
        text (str): The text to be converted to speech.

    Returns:
        bytes: The raw binary audio data for playback.

    Raises:
        ElevenLabsError: If there is an error communicating with the ElevenLabs API or processing the response.
    """
    logger.debug(f'Synthesizing speech from text with ElevenLabs. Text length: {len(text)} characters.')

    try:
        # Generate audio using the ElevenLabs SDK
        audio_iterator = elevenlabs_config.client.text_to_speech.convert(
            text=text,
            voice_id=elevenlabs_config.random_voice_id,  # Randomly chosen voice ID
            model_id=elevenlabs_config.model_id,
            output_format=elevenlabs_config.output_format,
        )

       # Ensure the response is an iterator
        if not hasattr(audio_iterator, '__iter__') or not hasattr(audio_iterator, '__next__'):
            logger.error('Invalid audio iterator response.')
            raise ElevenLabsError('Invalid audio iterator received from ElevenLabs API.')

        # Combine chunks into a single bytes object
        audio = b''.join(chunk for chunk in audio_iterator)

        # Validate audio
        if not audio:
            logger.error('No audio data received from ElevenLabs API.')
            raise ElevenLabsError('Empty audio data received from ElevenLabs API.')

        logger.info(f'Received ElevenLabs audio ({len(audio)} bytes).')
        return audio

    except Exception as e:
        logger.exception(f'Error synthesizing speech from text with Elevenlabs: {e}')
        raise ElevenLabsError(
            message=f'Failed to synthesize speech from text with ElevenLabs: {e}',
            original_exception=e,
        )
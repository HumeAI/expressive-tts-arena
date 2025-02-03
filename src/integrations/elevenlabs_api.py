"""
elevenlabs_api.py

This file defines the interaction with the ElevenLabs text-to-speech (TTS) API using the ElevenLabs Python SDK.
It includes functionality for API request handling and processing API responses.

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
from dataclasses import dataclass
from enum import Enum
import logging
import random
from typing import Literal, Optional, Tuple

# Third-Party Library Imports
from elevenlabs import ElevenLabs
from tenacity import retry, stop_after_attempt, wait_fixed, before_log, after_log

# Local Application Imports
from src.config import logger
from src.utils import validate_env_var


ElevenlabsVoiceName = Literal['Adam', 'Antoni', 'Rachel', 'Matilda']

class ElevenLabsVoice(Enum):
    ADAM = ('Adam', 'pNInz6obpgDQGcFmaJgB')
    ANTONI = ('Antoni', 'ErXwobaYiN019PkySvjV')
    RACHEL = ('Rachel', '21m00Tcm4TlvDq8ikWAM')
    MATILDA = ('Matilda', 'XrExE9yKIg1WjnnlVkGX')

    @property
    def voice_name(self) -> ElevenlabsVoiceName:
        """Returns the display name of the voice."""
        return self.value[0]

    @property
    def voice_id(self) -> str:
        """Returns the ElevenLabs voice ID."""
        return self.value[1]


@dataclass(frozen=True)
class ElevenLabsConfig:
    """Immutable configuration for interacting with the ElevenLabs TTS API."""
    api_key: str = validate_env_var('ELEVENLABS_API_KEY')
    model_id: str = 'eleven_multilingual_v2'  # ElevenLab's most emotionally expressive model
    output_format: str = 'mp3_44100_128'  # Output format of the generated audio

    def __post_init__(self):
        # Validate that required attributes are set
        if not self.api_key:
            raise ValueError('ElevenLabs API key is not set.')
        if not self.model_id:
            raise ValueError('ElevenLabs Model ID is not set.')
        if not self.output_format:
            raise ValueError('ElevenLabs Output Format is not set.')
    
    @property
    def client(self) -> ElevenLabs:
        """
        Lazy initialization of the ElevenLabs client.

        Returns:
            ElevenLabs: Configured client instance.
        """
        return ElevenLabs(api_key=self.api_key)

    @property
    def random_voice(self) -> ElevenLabsVoice:
        """
        Selects a random ElevenLabs voice.

        Returns:
            ElevenLabsVoice: A randomly selected voice enum member.
        """
        return random.choice(list(ElevenLabsVoice))


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
def text_to_speech_with_elevenlabs(text: str) -> Tuple[ElevenlabsVoiceName, bytes]:
    """
    Synthesizes text to speech using the ElevenLabs TTS API.

    Args:
        text (str): The text to be synthesized to speech.

    Returns:
        Tuple[ElevenlabsVoiceName, bytes]: A tuple containing the voice name used for speech synthesis
                                           and the raw binary audio data for playback.

    Raises:
        ElevenLabsError: If there is an error communicating with the ElevenLabs API or processing the response.
    """
    logger.debug(f'Synthesizing speech from text with ElevenLabs. Text length: {len(text)} characters.')

    # Get a random voice as an enum member.
    voice = elevenlabs_config.random_voice
    logger.debug(f"Selected voice: {voice.voice_name}")

    try:
        # Synthesize speech using the ElevenLabs SDK
        audio_iterator = elevenlabs_config.client.text_to_speech.convert(
            text=text,
            voice_id=voice.voice_id,
            model_id=elevenlabs_config.model_id,
            output_format=elevenlabs_config.output_format,
        )

        # Attempt to combine chunks into a single bytes object.
        # If audio_iterator is not iterable or invalid, an exception will be raised.
        try:
            audio = b''.join(chunk for chunk in audio_iterator)
        except Exception as iter_error:
            logger.error('Invalid audio iterator response.')
            raise ElevenLabsError('Invalid audio iterator received from ElevenLabs API.') from iter_error

        # Validate audio
        if not audio:
            logger.error('No audio data received from ElevenLabs API.')
            raise ElevenLabsError('Empty audio data received from ElevenLabs API.')

        logger.info(f'Received ElevenLabs audio ({len(audio)} bytes).')
        return voice.voice_name, audio

    except Exception as e:
        logger.exception(f'Error synthesizing speech from text with Elevenlabs: {e}')
        raise ElevenLabsError(
            message=f'Failed to synthesize speech from text with ElevenLabs: {e}',
            original_exception=e,
        )
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
import base64
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


@dataclass(frozen=True)
class ElevenLabsConfig:
    """Immutable configuration for interacting with the ElevenLabs TTS API."""

    api_key: str = validate_env_var("ELEVENLABS_API_KEY")

    def __post_init__(self):
        # Validate that required attributes are set
        if not self.api_key:
            raise ValueError("ElevenLabs API key is not set.")

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


# Initialize the ElevenLabs client
elevenlabs_config = ElevenLabsConfig()


@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(2),
    before=before_log(logger, logging.DEBUG),
    after=after_log(logger, logging.DEBUG),
    reraise=True,
)
def text_to_speech_with_elevenlabs(prompt: str, text: str) -> bytes:
    """
    Synthesizes text to speech using the ElevenLabs TTS API.

    Args:
        prompt (str): The original user prompt used as the voice description.
        text (str): The text to be synthesized to speech.

    Returns:
        bytes: The raw binary audio data for playback.

    Raises:
        ElevenLabsError: If there is an error communicating with the ElevenLabs API or processing the response.
    """
    logger.debug(
        f"Synthesizing speech with ElevenLabs. Text length: {len(text)} characters."
    )

    request_body = {"text": text, "voice_description": prompt}

    try:
        # Synthesize speech using the ElevenLabs SDK
        response = elevenlabs_config.client.text_to_voice.create_previews(
            voice_description=prompt,
            text=text,
        )

        previews = response.previews
        if not previews:
            msg = "No previews returned by ElevenLabs API."
            logger.error(msg)
            raise ElevenLabsError(message=msg)

        preview = random.choice(previews)
        base64_audio = preview.audio_base_64
        audio = base64.b64decode(base64_audio)
        return audio

    except Exception as e:
        logger.exception(f"Error synthesizing speech with ElevenLabs: {e}")
        raise ElevenLabsError(
            message=f"Failed to synthesize speech with ElevenLabs: {e}",
            original_exception=e,
        ) from e

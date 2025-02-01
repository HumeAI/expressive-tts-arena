"""
hume_api.py

This file defines the interaction with the Hume text-to-speech (TTS) API.
It includes functionality for API request handling and processing API responses.

Key Features:
- Encapsulates all logic related to the Hume TTS API.
- Implements retry logic for handling transient API errors.
- Handles received audio and processes it for playback on the web.
- Provides detailed logging for debugging and error tracking.

Classes:
- HumeConfig: Immutable configuration for interacting with Hume's text-to-speech API.
- HumeError: Custom exception for Hume API-related errors.

Functions:
- text_to_speech_with_hume: Synthesizes speech from text using Hume's text-to-speech API.
"""

# Standard Library Imports
from dataclasses import dataclass
import logging
import random
from typing import List, Optional

# Third-Party Library Imports
import requests
from tenacity import retry, stop_after_attempt, wait_fixed, before_log, after_log

# Local Application Imports
from src.config import logger
from src.utils import validate_env_var, truncate_text


@dataclass(frozen=True)
class HumeConfig:
    """Immutable configuration for interacting with the Hume TTS API."""
    tts_endpoint_url: str = 'https://api.hume.ai/v0/tts'
    api_key: str = validate_env_var('HUME_API_KEY')
    voices: List[str] = ('ITO', 'KORA', 'STELLA')  # List of available Hume voices
    audio_format: str = 'wav'
    headers: dict = None  # Headers for the API requests

    def __post_init__(self):
        # Validate required attributes
        if not self.api_key:
            raise ValueError('Hume API key is not set.')
        if not self.voices:
            raise ValueError('Hume voices list is empty. Please provide at least one voice.')
        if not self.audio_format:
            raise ValueError('Hume audio format is not set.')

        # Set headers dynamically after validation
        object.__setattr__(self, 'headers', {
            'X-Hume-Api-Key': f'{self.api_key}',
            'Content-Type': 'application/json',
        })

    @property
    def random_voice(self) -> str:
        """
        Randomly selects a voice from the available voices.

        Returns:
            str: A randomly chosen voice name.
        """
        return random.choice(self.voices)


class HumeError(Exception):
    """Custom exception for errors related to the Hume TTS API."""
    def __init__(self, message: str, original_exception: Optional[Exception] = None):
        super().__init__(message)
        self.original_exception = original_exception


# Initialize the Hume client
hume_config = HumeConfig()


@retry(
    stop=stop_after_attempt(1),
    wait=wait_fixed(2),
    before=before_log(logger, logging.DEBUG),
    after=after_log(logger, logging.DEBUG),
    reraise=True
)
def text_to_speech_with_hume(prompt: str, text: str) -> bytes:
    """
    Converts text to speech using the Hume TTS API and processes raw binary audio data.

    Args:
        prompt (str): The original user prompt (for debugging).
        text (str): The generated text to be converted to speech.

    Returns:
        bytes: The raw binary audio data for playback.

    Raises:
        HumeError: If there is an error communicating with the Hume TTS API.
    """
    logger.debug(f'Processing TTS with Hume. Prompt length: {len(prompt)} characters. Text length: {len(text)} characters.')

    request_body = {
        'text': text,
        'voice': {
            'name': hume_config.random_voice
        },
    }

    try:
        response = requests.post(
            url=hume_config.tts_endpoint_url,
            headers=hume_config.headers,
            json=request_body,
        )

        # Validate response
        if response.status_code != 200:
            logger.error(f'Hume TTS API Error: {response.status_code} - {response.text[:200]}... (truncated)')
            raise HumeError(f'Hume TTS API responded with status {response.status_code}: {response.text[:200]}')

        # Process response audio
        if response.headers.get('Content-Type', '').startswith('audio/'):
            audio = response.content  # Raw binary audio data
            logger.info(f'Received audio data from Hume ({len(audio)} bytes).')
            return audio

        raise HumeError(f'Unexpected Content-Type: {response.headers.get("Content-Type", "Unknown")}')

    except Exception as e:
        logger.exception(f'Error synthesizing speech from text with Hume: {e}')
        raise HumeError(
            message=f'Failed to synthesize speech from text with Hume: {e}',
            original_exception=e,
        )
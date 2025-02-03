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
- HumeConfig: Immutable configuration for interacting with Hume's TTS API.
- HumeError: Custom exception for Hume API-related errors.

Functions:
- text_to_speech_with_hume: Synthesizes speech from text using Hume's TTS API.
"""

# Standard Library Imports
from dataclasses import dataclass
import logging
import random
from typing import List, Literal, Optional, Tuple

# Third-Party Library Imports
import requests
from tenacity import retry, stop_after_attempt, wait_fixed, before_log, after_log

# Local Application Imports
from src.config import logger
from src.utils import validate_env_var, truncate_text


HumeVoiceName = Literal["ITO", "KORA", "STELLA", "DACHER"]


@dataclass(frozen=True)
class HumeConfig:
    """Immutable configuration for interacting with the Hume TTS API."""

    api_key: str = validate_env_var("HUME_API_KEY")
    tts_endpoint_url: str = "https://api.hume.ai/v0/tts"
    voice_names: List[HumeVoiceName] = ("ITO", "KORA", "STELLA", "DACHER")
    audio_format: str = "wav"
    headers: dict = None

    def __post_init__(self):
        # Validate required attributes
        if not self.api_key:
            raise ValueError("Hume API key is not set.")
        if not self.tts_endpoint_url:
            raise ValueError("Hume TTS endpoint URL is not set.")
        if not self.voice_names:
            raise ValueError("Hume voice names list is not set.")
        if not self.audio_format:
            raise ValueError("Hume audio format is not set.")

        # Set headers dynamically after validation
        object.__setattr__(
            self,
            "headers",
            {
                "X-Hume-Api-Key": f"{self.api_key}",
                "Content-Type": "application/json",
            },
        )


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
    reraise=True,
)
def text_to_speech_with_hume(
    prompt: str, text: str, voice_name: HumeVoiceName
) -> bytes:
    """
    Synthesizes text to speech using the Hume TTS API and processes raw binary audio data.

    Args:
        prompt (str): The original user prompt (for debugging).
        text (str): The generated text to be converted to speech.
        voice_name (HumeVoiceName): Name of the voice Hume will use when synthesizing speech.

    Returns:
        voice_name: The name of the voice used for speech synthesis.
        bytes: The raw binary audio data for playback.

    Raises:
        HumeError: If there is an error communicating with the Hume TTS API.
    """
    logger.debug(
        f"Processing TTS with Hume. Prompt length: {len(prompt)} characters. Text length: {len(text)} characters."
    )

    request_body = {
        "text": text,
        "voice": {"name": voice_name},
    }

    try:
        # Synthesize speech using the Hume TTS API
        response = requests.post(
            url=hume_config.tts_endpoint_url,
            headers=hume_config.headers,
            json=request_body,
        )

        # Validate response
        if response.status_code != 200:
            logger.error(
                f"Hume TTS API Error: {response.status_code} - {response.text[:200]}... (truncated)"
            )
            raise HumeError(
                f"Hume TTS API responded with status {response.status_code}: {response.text[:200]}"
            )

        # Process response audio
        if response.headers.get("Content-Type", "").startswith("audio/"):
            audio = response.content  # Raw binary audio data
            logger.info(f"Received audio data from Hume ({len(audio)} bytes).")
            return voice_name, audio

        raise HumeError(
            f'Unexpected Content-Type: {response.headers.get("Content-Type", "Unknown")}'
        )

    except Exception as e:
        logger.exception(f"Error synthesizing speech from text with Hume: {e}")
        raise HumeError(
            message=f"Failed to synthesize speech from text with Hume: {e}",
            original_exception=e,
        )


def get_random_hume_voice_names() -> Tuple[HumeVoiceName, HumeVoiceName]:
    """
    Get two random Hume voice names.

    Voices:
        - ITO
        - KORA
        - STELLA
        - DACHER
    """
    return tuple(random.sample(hume_config.voice_names, 2))

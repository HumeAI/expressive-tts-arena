"""
hume_api.py

This file defines the interaction with the Hume TTS API, focusing on converting text to audio.
It includes functionality for input validation, API request handling, and processing API responses.

Key Features:
- Encapsulates all logic related to the Hume TTS API.
- Implements retry logic for handling transient API errors.
- Handles received audio and processes it for playback on the web.
- Provides detailed logging for debugging and error tracking.

Classes:
- HumeException: Custom exception for TTS API-related errors.
- HumeConfig: Immutable configuration for interacting with the TTS API.

Functions:
- text_to_speech_with_hume: Converts text to speech using the Hume TTS API with input validation and retry logic.
"""

# Standard Library Imports
import logging
from dataclasses import dataclass
from typing import Optional
# Third-Party Library Imports
import requests
from tenacity import retry, stop_after_attempt, wait_fixed, before_log, after_log
# Local Application Imports
from src.config import logger
from src.utils import validate_env_var, truncate_text


@dataclass(frozen=True)
class HumeConfig:
    """Immutable configuration for interacting with the TTS API."""
    tts_endpoint_url: str = "https://api.hume.ai/v0/tts"
    api_key: str = validate_env_var("HUME_API_KEY")
    voice: str = "KORA"
    audio_format: str = 'wav'
    headers: dict = None

    def __post_init__(self):
        # Dynamically set headers after initialization
        object.__setattr__(self, "headers", { 
            'X-Hume-Api-Key': f"{self.api_key}",
            'Content-Type': 'application/json',
        })


class HumeException(Exception):
    """Custom exception for errors related to the Hume TTS API."""
    def __init__(self, message: str, original_exception: Optional[Exception] = None):
        super().__init__(message)
        self.original_exception = original_exception


# Initialize the Hume client
hume_config = HumeConfig()


@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(2),
    before=before_log(logger, logging.DEBUG),
    after=after_log(logger, logging.DEBUG),
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
        HumeException: If there is an error communicating with the Hume TTS API.
    """
    logger.debug(f"Preparing TTS request for prompt: {truncate_text(prompt)}")
    logger.debug(f"Generated text for TTS: {truncate_text(text)}")

    request_body = {
        "text": text,
        "voice": {"name": hume_config.voice},
        # "voice_description": prompt, # <-- breaking request!?
        # "format": hume_config.audio_format, # <-- breaking request!?
    }

    try:
        response = requests.post(
            url=hume_config.tts_endpoint_url,
            headers=hume_config.headers,
            json=request_body,
        )

        # Log the status and content type for debugging
        logger.debug(f"Hume TTS API Response Status: {response.status_code}")

        if response.status_code != 200:
            logger.error(f"Hume TTS API Error: {response.status_code} - {response.text[:200]}... (truncated)")
            raise HumeException(f"Hume TTS API responded with status {response.status_code}: {response.text}")

        # If Content-Type is audio, return the binary audio data
        if response.headers.get("Content-Type", "").startswith("audio/"):
            audio_data = response.content  # Raw binary audio data
            logger.debug(f"Received binary audio data: {len(audio_data)} bytes")
            return audio_data

        # Unexpected content type
        logger.error(f"Unexpected Content-Type: {response.headers.get('Content-Type', 'Unknown')}")
        raise HumeException(f"Unexpected Content-Type: {response.headers.get('Content-Type', 'Unknown')}")

    except requests.exceptions.RequestException as e:
        logger.exception("Request to Hume TTS API failed.")
        raise HumeException(
            message=f"Failed to communicate with Hume TTS API: {e}",
            original_exception=e,
        )
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        raise HumeException(
            message=f"Unexpected error while processing the Hume TTS response: {e}",
            original_exception=e,
        )
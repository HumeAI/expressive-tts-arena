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
import base64
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


@dataclass(frozen=True)
class HumeConfig:
    """Immutable configuration for interacting with the Hume TTS API."""

    api_key: str = validate_env_var("HUME_API_KEY")
    url: str = "https://test-api.hume.ai/v0/tts/octave"
    headers: dict = None

    def __post_init__(self):
        # Validate required attributes
        if not self.api_key:
            raise ValueError("Hume API key is not set.")
        if not self.url:
            raise ValueError("Hume TTS endpoint URL is not set.")

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
    stop=stop_after_attempt(3),
    wait=wait_fixed(2),
    before=before_log(logger, logging.DEBUG),
    after=after_log(logger, logging.DEBUG),
    reraise=True,
)
def text_to_speech_with_hume(prompt: str, text: str) -> bytes:
    """
    Synthesizes text to speech using the Hume TTS API and processes raw binary audio data.

    Args:
        prompt (str): The original user prompt to use as the description for generating the voice.
        text (str): The generated text to be converted to speech.

    Returns:
        bytes: The raw binary audio data for playback.

    Raises:
        HumeError: If there is an error communicating with the Hume TTS API or parsing the response.
    """
    logger.debug(
        f"Processing TTS with Hume. Prompt length: {len(prompt)} characters. Text length: {len(text)} characters."
    )

    request_body = {"utterances": [{"text": text, "description": prompt}]}

    try:
        # Synthesize speech using the Hume TTS API
        response = requests.post(
            url=hume_config.url,
            headers=hume_config.headers,
            json=request_body,
        )
        response.raise_for_status()
        response_data = response.json()
    except requests.RequestException as re:
        request_error_msg = f"Error communicating with Hume TTS API: {re}"
        logger.exception(request_error_msg)
        raise HumeError(request_error_msg) from re

    try:
        # Safely extract the generation result from the response JSON
        generations = response_data.get("generations", [])
        if not generations:
            logger.error("Missing 'audio' data in the response.")
            raise HumeError("Missing audio data in response from Hume TTS API")
        generation = generations[0]
        base64_audio = generation.get("audio")
        # Decode base64 encoded audio
        audio = base64.b64decode(base64_audio)
    except (KeyError, TypeError, base64.binascii.Error) as ae:
        logger.exception(f"Error processing audio data: {ae}")
        raise HumeError(f"Error processing audio data from Hume TTS API: {ae}") from ae

    logger.info(f"Received audio data from Hume ({len(audio)} bytes).")
    return audio

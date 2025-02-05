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
import os
import random
from typing import Literal, Optional

# Third-Party Library Imports
import requests
from tenacity import retry, stop_after_attempt, wait_fixed, before_log, after_log

# Local Application Imports
from src.config import logger
from src.utils import save_base64_audio_to_file, validate_env_var


HumeSupportedFileFormat = Literal["mp3", "pcm", "wav"]
""" Support audio file formats for the Hume TTS API"""


@dataclass(frozen=True)
class HumeConfig:
    """Immutable configuration for interacting with the Hume TTS API."""

    api_key: str = validate_env_var("HUME_API_KEY")
    url: str = "https://test-api.hume.ai/v0/tts/octave"
    headers: dict = None
    file_format: HumeSupportedFileFormat = "mp3"

    def __post_init__(self):
        # Validate required attributes
        if not self.api_key:
            raise ValueError("Hume API key is not set.")
        if not self.url:
            raise ValueError("Hume TTS endpoint URL is not set.")
        if not self.file_format:
            raise ValueError("Hume TTS file format is not set.")

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
    Synthesizes text to speech using the Hume TTS API, processes audio data, and writes audio to a file.

    Args:
        prompt (str): The original user prompt to use as the description for generating the voice.
        text (str): The generated text to be converted to speech.

    Returns:
        str: The relative path for the file the synthesized audio was written to.

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

        generations = response_data.get("generations")
        if not generations:
            msg = "No generations returned by Hume API."
            logger.error(msg)
            raise HumeError(msg)

        # Extract the base64 encoded audio and generation ID from the generation
        generation = generations[0]
        generation_id = generation.get("generation_id")
        base64_audio = generation.get("audio")
        filename = f"{generation_id}.mp3"

        # Write audio to file and return the relative path
        return save_base64_audio_to_file(base64_audio, filename)

    except Exception as e:
        logger.exception(f"Error synthesizing speech with Hume: {e}")
        raise HumeError(
            message=f"Failed to synthesize speech with Hume: {e}",
            original_exception=e,
        ) from e

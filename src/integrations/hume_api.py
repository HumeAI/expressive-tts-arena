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
import logging
from dataclasses import dataclass
from typing import Any, Dict, Literal, Optional, Tuple, Union

# Third-Party Library Imports
import requests
from requests.exceptions import HTTPError
from tenacity import after_log, before_log, retry, stop_after_attempt, wait_fixed

# Local Application Imports
from src.config import logger, validate_env_var
from src.constants import CLIENT_ERROR_CODE, SERVER_ERROR_CODE
from src.utils import save_base64_audio_to_file

HumeSupportedFileFormat = Literal["mp3", "pcm", "wav"]
""" Support audio file formats for the Hume TTS API"""


@dataclass(frozen=True)
class HumeConfig:
    """Immutable configuration for interacting with the Hume TTS API."""

    api_key: Optional[str] = None
    url: str = "https://test-api.hume.ai/v0/tts/octave"
    headers: dict = None
    file_format: HumeSupportedFileFormat = "mp3"

    def __post_init__(self):
        # Validate required attributes
        if not self.api_key:
            api_key = validate_env_var("HUME_API_KEY")
            object.__setattr__(self, "api_key", api_key)
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
        self.message = message


class UnretryableHumeError(HumeError):
    """Custom exception for errors related to the Hume TTS API that should not be retried."""

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
def text_to_speech_with_hume(
    character_description: str, text: str, num_generations: int = 1
) -> Union[Tuple[str, str], Tuple[str, str, str, str]]:
    """
    Synthesizes text to speech using the Hume TTS API, processes audio data, and writes audio to a file.

    This function sends a POST request to the Hume TTS API with a character description and text
    to be converted to speech. Depending on the specified number of generations (allowed values: 1 or 2),
    the API returns one or two generations. For each generation, the function extracts the base64-encoded
    audio and the generation ID, saves the audio as an MP3 file via the `save_base64_audio_to_file` helper,
    and returns the relevant details.

    Args:
        character_description (str): A description of the character, which is used as contextual input
            for generating the voice.
        text (str): The text to be converted to speech.
        num_generations (int, optional): The number of audio generations to request from the API.
            Allowed values are 1 or 2. If 1, only a single generation is processed; if 2, a second
            generation is expected in the API response. Defaults to 1.

    Returns:
        Union[Tuple[str, str], Tuple[str, str, str, str]]:
            - If num_generations == 1: (generation_a_id, audio_a_path).
            - If num_generations == 2: (generation_a_id, audio_a_path, generation_b_id, audio_b_path).

    Raises:
        ValueError: If num_generations is not 1 or 2.
        HumeError: If there is an error communicating with the Hume TTS API or parsing its response.
        UnretryableHumeError: If a client-side HTTP error (status code in the 4xx range) is encountered.
        Exception: Any other exceptions raised during the request or processing will be wrapped and
                   re-raised as HumeError.
    """
    logger.debug(
        f"Processing TTS with Hume. Prompt length: {len(character_description)} characters. "
        f"Text length: {len(text)} characters."
    )

    if num_generations < 1 or num_generations > 2:
        raise ValueError("Invalid number of generations specified. Must be 1 or 2.")

    request_body = {
        "utterances": [{"text": text, "description": character_description or None}],
        "format": {
            "type": hume_config.file_format,
        },
        "num_generations": num_generations,
    }

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
        generation_a = generations[0]
        generation_a_id, audio_a_path = parse_hume_tts_generation(generation_a)

        if num_generations == 1:
            return (generation_a_id, audio_a_path)

        generation_b = generations[1]
        generation_b_id, audio_b_path = parse_hume_tts_generation(generation_b)
        return (generation_a_id, audio_a_path, generation_b_id, audio_b_path)

    except Exception as e:
        if (
            isinstance(e, HTTPError)
            and CLIENT_ERROR_CODE <= e.response.status_code < SERVER_ERROR_CODE
        ):
            raise UnretryableHumeError(
                message=f"{e.response.text}",
                original_exception=e,
            ) from e

        raise HumeError(
            message=f"{e}",
            original_exception=e,
        ) from e


def parse_hume_tts_generation(generation: Dict[str, Any]) -> Tuple[str, str]:
    """
    Parse a Hume TTS generation response and save the decoded audio as an MP3 file.

    This function extracts the generation ID and the base64-encoded audio from the provided
    dictionary. It then decodes and saves the audio data to an MP3 file, naming the file using
    the generation ID. Finally, it returns a tuple containing the generation ID and the file path
    of the saved audio.

    Args:
        generation (Dict[str, Any]): A dictionary representing the TTS generation response from Hume.
            Expected keys are:
                - "generation_id" (str): A unique identifier for the generated audio.
                - "audio" (str): A base64 encoded string of the audio data.

    Returns:
        Tuple[str, str]: A tuple containing:
            - generation_id (str): The unique identifier for the audio generation.
            - audio_path (str): The filesystem path where the audio file was saved.

    Raises:
        KeyError: If the "generation_id" or "audio" key is missing from the generation dictionary.
        Exception: Propagates any exceptions raised by save_base64_audio_to_file, such as errors during
                   the decoding or file saving process.
    """
    generation_id = generation.get("generation_id")
    if generation_id is None:
        raise KeyError("The generation dictionary is missing the 'generation_id' key.")

    base64_audio = generation.get("audio")
    if base64_audio is None:
        raise KeyError("The generation dictionary is missing the 'audio' key.")

    filename = f"{generation_id}.mp3"
    audio_file_path = save_base64_audio_to_file(base64_audio, filename)
    return generation_id, audio_file_path

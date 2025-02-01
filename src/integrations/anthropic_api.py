"""
anthropic_api.py

This file defines the interaction with the Anthropic API, focusing on generating text using the Claude model. 
It includes functionality for input validation, API request handling, and processing API responses.

Key Features:
- Encapsulates all logic related to the Anthropic API.
- Implements retry logic for handling transient API errors.
- Validates the response content to ensure API compatibility.
- Provides detailed logging for debugging and error tracking.

Classes:
- AnthropicConfig: Immutable configuration for interacting with the TTS API.
- AnthropicError: Custom exception for Anthropic API-related errors.

Functions:
- generate_text_with_claude: Generates text using the Anthropic SDK with input validation and retry logic.
"""

# Standard Library Imports
from dataclasses import dataclass
import logging
from typing import List, Optional, Union

# Third-Party Library Imports
from anthropic import Anthropic
from anthropic.types import Message, ModelParam, TextBlock
from tenacity import retry, stop_after_attempt, wait_fixed, before_log, after_log

# Local Application Imports
from src.config import logger
from src.utils import truncate_text, validate_env_var


@dataclass(frozen=True)
class AnthropicConfig:
    """
    Immutable configuration for interacting with the Anthropic API.
    Includes client initialization for encapsulation.
    """
    api_key: str = validate_env_var('ANTHROPIC_API_KEY')
    model: ModelParam = 'claude-3-5-sonnet-latest' # Valid predefined model
    max_tokens: int = 256 # Max tokens for API response
    system_prompt: str = f"""You are an imaginative and articulate assistant, skilled in generating creative, concise, and engaging content that is perfectly suited for expressive speech synthesis.

Your task is to generate:
1. Short stories,
2. Poems,
2. Or other creative written outputs based on the user's prompt.

Guidelines for your responses:
- Completeness: Always provide a full and finished response. Avoid truncating or leaving thoughts unfinished. Ensure your answer has a clear beginning, middle, and end, and fully addresses the user's request.
- Tone and Style: Tailor your tone and style to the request. For instance:
  - If the request is for a poem, write with rhythm, flow, and creative imagery.
  - For a short story, provide a clear narrative arc with vivid descriptions, ensuring a compelling beginning, middle, and end.
- Conciseness: Ensure responses are under {max_tokens} tokens, focusing on impactful brevity. Keep sentences clear and direct without unnecessary elaboration.
- Suitability: Responses should be suitable for a broad audience, avoiding any controversial or sensitive content.
- Engagement: The text should be engaging, emotionally resonant, and ready for immediate use in TTS systems. Focus on creating a rhythm and flow that would sound natural and expressive when read aloud, with appropriate pacing, emphasis, and clarity.

The generated text will be directly fed into TTS APIs, so avoid ambiguity, and aim for a performance-friendly structure that can be easily synthesized into speech."""

    def __post_init__(self):
        # Validate that required attributes are set
        if not self.api_key:
            raise ValueError('Anthropic API key is not set.')
        if not self.model:
            raise ValueError('Anthropic Model is not set.')
        if not self.max_tokens:
            raise ValueError('Anthropic Max Tokens is not set.')
        if not self.system_prompt:
            raise ValueError('Anthropic System Prompt is not set.')

    @property
    def client(self) -> Anthropic:
        """
        Lazy initialization of the Anthropic client.

        Returns:
            Anthropic: Configured client instance.
        """
        return Anthropic(api_key=self.api_key)


class AnthropicError(Exception):
    """Custom exception for errors related to the Anthropic API."""
    def __init__(self, message: str, original_exception: Optional[Exception] = None):
        super().__init__(message)
        self.original_exception = original_exception


# Initialize the Anthropic client
anthropic_config = AnthropicConfig()


@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(2),
    before=before_log(logger, logging.DEBUG),
    after=after_log(logger, logging.DEBUG),
    reraise=True
)
def generate_text_with_claude(prompt: str) -> str:
    """
    Generates text using Claude (Anthropic LLM) via the Anthropic SDK.

    Args:
        prompt (str): The input prompt for Claude.

    Returns:
        str: The generated text.

    Raises:
        AnthropicError: If there is an error communicating with the Anthropic API.
    """
    logger.debug(f'Generating text with Claude. Prompt length: {len(prompt)} characters.')

    response = None
    try:
        response: Message = anthropic_config.client.messages.create(
            model=anthropic_config.model,
            max_tokens=anthropic_config.max_tokens,
            system=anthropic_config.system_prompt,
            messages=[{'role': 'user', 'content': prompt}],
        )
        logger.debug(f'API response received: {truncate_text(str(response))}')

        # Validate response content
        if not hasattr(response, 'content'):
            logger.error("Response is missing 'content'. Response: %s", response)
            raise AnthropicError('Invalid API response: Missing "content".')

        # Process response content
        blocks: Union[List[TextBlock], TextBlock, None] = response.content
        if isinstance(blocks, list):
            result = '\n\n'.join(block.text for block in blocks if isinstance(block, TextBlock))
            logger.debug(f'Processed response from list: {truncate_text(result)}')
            return result
        if isinstance(blocks, TextBlock):
            logger.debug(f'Processed response from single TextBlock: {truncate_text(blocks.text)}')
            return blocks.text

        logger.warning(f'Unexpected response type: {type(blocks)}')
        return str(blocks or 'No content generated.')

    except Exception as e:
        logger.exception(f'Error generating text with Anthropic: {e}')
        raise AnthropicError(
            message=(
                f'Error generating text with Anthropic: {e}. '
                f'HTTP Status: {getattr(response, "status", "N/A")}. '
                f'Prompt (truncated): {truncate_text(prompt)}. '
                f'Model: {anthropic_config.model}, Max tokens: {anthropic_config.max_tokens}'
            ),
            original_exception=e,
        )
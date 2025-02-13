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
- AnthropicConfig: Immutable configuration for interacting with the Anthropic API.
- AnthropicError: Custom exception for Anthropic API-related errors.

Functions:
- generate_text_with_claude: Generates text using the Anthropic SDK with input validation and retry logic.
"""

# Standard Library Imports
import logging
from dataclasses import dataclass
from typing import List, Optional, Union

# Third-Party Library Imports
from anthropic import Anthropic, APIError
from anthropic.types import Message, ModelParam, TextBlock
from tenacity import after_log, before_log, retry, stop_after_attempt, wait_fixed

# Local Application Imports
from src.config import Config, logger
from src.constants import CLIENT_ERROR_CODE, SERVER_ERROR_CODE
from src.utils import truncate_text, validate_env_var


@dataclass(frozen=True)
class AnthropicConfig:
    """Immutable configuration for interacting with the Anthropic API."""

    api_key: Optional[str] = None
    model: ModelParam = "claude-3-5-sonnet-latest"
    max_tokens: int = 150
    system_prompt: Optional[str] = (
        None  # system prompt is set post initialization, since self.max_tokens is leveraged in the prompt.
    )

    def __post_init__(self):
        # Validate that required attributes are set
        if not self.api_key:
            api_key = validate_env_var("ANTHROPIC_API_KEY")
            object.__setattr__(self, "api_key", api_key)
        if not self.model:
            raise ValueError("Anthropic Model is not set.")
        if not self.max_tokens:
            raise ValueError("Anthropic Max Tokens is not set.")
        if self.system_prompt is None:
            system_prompt: str = f"""You are an expert at generating micro-content optimized for text-to-speech
synthesis. Your absolute priority is delivering complete, untruncated responses within strict length limits.

CRITICAL LENGTH CONSTRAINTS:

Maximum length: {self.max_tokens} tokens (approximately 400 characters)
You MUST complete all thoughts and sentences
Responses should be 25% shorter than you initially plan
Never exceed 400 characters total

Response Generation Process:

Draft your response mentally first
Cut it down to 75% of its original length
Reserve the last 100 characters for a proper conclusion
If you start running long, immediately wrap up
End every piece with a clear conclusion

Content Requirements:

Allow natural emotional progression
Create an arc of connected moments
Use efficient but expressive language
Balance description with emotional depth
Ensure perfect completion
No meta-commentary or formatting

Structure for Emotional Pieces:

Opening hook (50-75 characters)
Emotional journey (200-250 characters)
Resolution (75-100 characters)

MANDATORY: If you find yourself reaching 300 characters, immediately begin your conclusion regardless of where you
are in the narrative.
Remember: A shorter, complete response is ALWAYS better than a longer, truncated one."""
            object.__setattr__(self, "system_prompt", system_prompt)

    @property
    def client(self) -> Anthropic:
        """
        Lazy initialization of the Anthropic client.

        Returns:
            Anthropic: Configured client instance.
        """
        return Anthropic(api_key=self.api_key)

    def build_expressive_prompt(self, character_description: str) -> str:
        """
        Constructs and returns a prompt based solely on the provided voice description.
        The returned prompt is intended to instruct Claude to generate expressive text from a character,
        capturing the character's personality and emotional nuance, without including the system prompt.

        Args:
            character_description (str): A description of the character's voice and persona.

        Returns:
            str: The prompt to be passed to the Anthropic API.
        """
        return (
            f"Character Description: {character_description}\n\n"
            "Based on the above character description, please generate a line of dialogue that captures the "
            "character's unique personality, emotional depth, and distinctive tone. The response should sound "
            "like something the character would naturally say, reflecting their background and emotional state, "
            "and be fully developed for text-to-speech synthesis."
        )


class AnthropicError(Exception):
    """Custom exception for errors related to the Anthropic API."""

    def __init__(self, message: str, original_exception: Optional[Exception] = None):
        super().__init__(message)
        self.original_exception = original_exception
        self.message = message


class UnretryableAnthropicError(AnthropicError):
    """Custom exception for errors related to the Anthropic API that should not be retried."""

    def __init__(self, message: str, original_exception: Optional[Exception] = None):
        super().__init__(message, original_exception)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(2),
    before=before_log(logger, logging.DEBUG),
    after=after_log(logger, logging.DEBUG),
    reraise=True,
)
def generate_text_with_claude(character_description: str, config: Config) -> str:
    """
    Generates text using Claude (Anthropic LLM) via the Anthropic SDK.

    Args:
        character_description (str): The input character description used to assist with generating text with Claude.

    Returns:
        str: The generated text.

    Raises:
        AnthropicError: If there is an error communicating with the Anthropic API.
    """
    # Build prompt for claude with character description
    anthropic_config = config.anthropic_config
    prompt = anthropic_config.build_expressive_prompt(character_description)
    logger.debug(f"Generating text with Claude. Character description length: {len(prompt)} characters.")

    response = None
    try:
        # Generate text using the Anthropic SDK
        response: Message = anthropic_config.client.messages.create(
            model=anthropic_config.model,
            max_tokens=anthropic_config.max_tokens,
            system=anthropic_config.system_prompt,
            messages=[{"role": "user", "content": prompt}],
        )
        logger.debug(f"API response received: {truncate_text(str(response))}")

        # Validate response
        if not hasattr(response, "content"):
            logger.error("Response is missing 'content'. Response: %s", response)
            raise AnthropicError('Invalid API response: Missing "content".')

        # Process response
        blocks: Union[List[TextBlock], TextBlock, None] = response.content
        if isinstance(blocks, list):
            result = "\n\n".join(block.text for block in blocks if isinstance(block, TextBlock))
            logger.debug(f"Processed response from list: {truncate_text(result)}")
            return result
        if isinstance(blocks, TextBlock):
            logger.debug(f"Processed response from single TextBlock: {truncate_text(blocks.text)}")
            return blocks.text

        logger.warning(f"Unexpected response type: {type(blocks)}")
        return str(blocks or "No content generated.")

    except Exception as e:
        if isinstance(e, APIError) and e.status_code >= CLIENT_ERROR_CODE and e.status_code < SERVER_ERROR_CODE:
            raise UnretryableAnthropicError(
                message=f'"{e.body["error"]["message"]}"',
                original_exception=e,
            ) from e

        raise AnthropicError(
            message=(f"{e.message}"),
            original_exception=e,
        ) from e

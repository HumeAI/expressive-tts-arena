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
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union, cast

# Third-Party Library Imports
from anthropic import Anthropic, APIError
from anthropic.types import Message, ModelParam, TextBlock, ToolUseBlock
from tenacity import after_log, before_log, retry, stop_after_attempt, wait_fixed

# Local Application Imports
from src.config import Config, logger
from src.constants import CLIENT_ERROR_CODE, SERVER_ERROR_CODE
from src.utils import truncate_text, validate_env_var

PROMPT_TEMPLATE: str = (
    """You are an expert at generating micro-content optimized for text-to-speech synthesis.
Your absolute priority is delivering complete, untruncated responses within strict length limits.

CRITICAL LENGTH CONSTRAINTS:
- Maximum length: {max_tokens} tokens (approximately 400 characters)
- You MUST complete all thoughts and sentences
- Responses should be 25% shorter than you initially plan
- Never exceed 400 characters total

Response Generation Process:
- Draft your response mentally first
- ut it down to 75% of its original length
- Reserve the last 100 characters for a proper conclusion
- If you start running long, immediately wrap up
- End every piece with a clear conclusion

Content Requirements:
- Allow natural emotional progression
- Create an arc of connected moments
- Use efficient but expressive language
- Balance description with emotional depth
- Ensure perfect completion
- No meta-commentary or formatting

Structure for Emotional Pieces:
- Opening hook (50-75 characters)
- Emotional journey (200-250 characters)
- Resolution (75-100 characters)

MANDATORY: If you find yourself reaching 300 characters, immediately begin your conclusion regardless of
where you are in the narrative.

Remember: A shorter, complete response is ALWAYS better than a longer, truncated one."""
)

@dataclass(frozen=True)
class AnthropicConfig:
    """Immutable configuration for interacting with the Anthropic API."""

    api_key: str = field(init=False)
    system_prompt: str = field(init=False)
    model: ModelParam = "claude-3-5-sonnet-latest"
    max_tokens: int = 150

    def __post_init__(self) -> None:
        # Validate required non-computed attributes.
        if not self.model:
            raise ValueError("Anthropic Model is not set.")
        if not self.max_tokens:
            raise ValueError("Anthropic Max Tokens is not set.")

        # Compute the API key from the environment.
        computed_api_key = validate_env_var("ANTHROPIC_API_KEY")
        object.__setattr__(self, "api_key", computed_api_key)

        # Compute the system prompt using max_tokens and other logic.
        computed_prompt = PROMPT_TEMPLATE.format(max_tokens=self.max_tokens)
        object.__setattr__(self, "system_prompt", computed_prompt)

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

    def __init__(self, message: str, original_exception: Optional[Exception] = None) -> None:
        super().__init__(message)
        self.original_exception = original_exception
        self.message = message


class UnretryableAnthropicError(AnthropicError):
    """Custom exception for errors related to the Anthropic API that should not be retried."""

    def __init__(self, message: str, original_exception: Optional[Exception] = None) -> None:
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

    This function includes retry logic and error translation. It raises a custom
    UnretryableAnthropicError for API errors deemed unretryable and AnthropicError
    for other errors.

    Args:
        character_description (str): The input character description used to assist with generating text.
        config (Config): Application configuration including Anthropic settings.

    Returns:
        str: The generated text.

    Raises:
        UnretryableAnthropicError: For errors that should not be retried.
        AnthropicError: For other errors communicating with the Anthropic API.
    """
    try:
        anthropic_config = config.anthropic_config
        prompt = anthropic_config.build_expressive_prompt(character_description)
        logger.debug(f"Generating text with Claude. Character description length: {len(prompt)} characters.")

        # Ensure system_prompt is set (guaranteed by __post_init__)
        assert anthropic_config.system_prompt is not None, "system_prompt must be set."

        response: Message = anthropic_config.client.messages.create(
            model=anthropic_config.model,
            max_tokens=anthropic_config.max_tokens,
            system=anthropic_config.system_prompt,
            messages=[{"role": "user", "content": prompt}],
        )
        logger.debug(f"API response received: {truncate_text(str(response))}")

        if not hasattr(response, "content") or response.content is None:
            logger.error("Response is missing 'content'. Response: %s", response)
            raise AnthropicError('Invalid API response: Missing "content".')

        blocks: Union[List[Union[TextBlock, ToolUseBlock]], TextBlock, None] = response.content

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
        # If the error is an APIError, check if it's unretryable.
        if isinstance(e, APIError):
            status_code: Optional[int] = getattr(e, "status_code", None)
            if status_code is not None and CLIENT_ERROR_CODE <= status_code < SERVER_ERROR_CODE:
                error_body: Any = e.body
                error_message: str = "Unknown error"
                if isinstance(error_body, dict):
                    error_message = cast(Dict[str, Any], error_body).get("error", {}).get("message", "Unknown error")
                raise UnretryableAnthropicError(
                    message=f'"{error_message}"',
                    original_exception=e,
                ) from e

        # For all other errors, wrap them in an AnthropicError.
        raise AnthropicError(
            message=str(e),
            original_exception=e,
        ) from e

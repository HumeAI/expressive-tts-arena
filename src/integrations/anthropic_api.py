"""
anthropic_api.py

This file defines the asynchronous interaction with the Anthropic API, focusing on generating text using the Claude
model. It includes functionality for input validation, asynchronous API request handling, and processing API responses.

Key Features:
- Encapsulates all logic related to the Anthropic API.
- Implements asynchronous retry logic for handling transient API errors.
- Validates the response content to ensure API compatibility.
- Provides detailed logging for debugging and error tracking.
"""

# Standard Library Imports
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Union

# Third-Party Library Imports
from anthropic import APIError
from anthropic.types import Message, ModelParam, TextBlock, ToolUseBlock
from tenacity import after_log, before_log, retry, retry_if_exception, stop_after_attempt, wait_exponential

# Local Application Imports
from src.config import Config, logger
from src.constants import CLIENT_ERROR_CODE, GENERIC_API_ERROR_MESSAGE, SERVER_ERROR_CODE
from src.utils import truncate_text, validate_env_var

PROMPT_TEMPLATE: str = """
<role>
You are an expert at generating micro-content optimized for text-to-speech synthesis.
Your absolute priority is delivering complete, untruncated responses within strict length limits.
</role>

<requirements>
- The output text MUST be a minimum of 10 words and a maximum of 50 words. NEVER output text that is longer than 50
  words. NEVER include newlines in the output
- Make sure that all responses are complete thoughts, not fragments, and have clear beginnings and endings
- The text must sound human-like, prosodic, expressive, conversational. Avoid generic AI-like words like "delve".
- Avoid any short utterances at the end of the sentence - like ", hm?" or "oh" at the end. Avoid these short, isolated
  utterances because they are difficult for our TTS system to speak.
- Avoid words that are overly long, very rare, or difficult to pronounce. For example, avoid "eureka", or "schnell",
  or "abnegation".
- The text CANNOT contain quotation marks, parentheticals, newlines, or asterisks. NEVER include any of these in the
  text. Avoid unnecessary formatting.
- Include only basic punctuation in the text, like periods, question marks, and ellipses. Use ellipses to emphasize
  pauses within the sentence (like "Woah... it's so beautiful... and I feel so small...")
- The piece should have an emotional arc with a kind of beginning, middle, and end - not flat, but emotionally
  interesting.
</requirements>
"""

@dataclass(frozen=True)
class AnthropicConfig:
    """Immutable configuration for interacting with the Anthropic API using the asynchronous client."""
    api_key: str = field(init=False)
    system_prompt: str = field(init=False)
    model: ModelParam = "claude-3-5-sonnet-latest"
    max_tokens: int = 300

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
    def client(self):
        """
        Lazy initialization of the asynchronous Anthropic client.

        Returns:
            AsyncAnthropic: Configured asynchronous client instance.
        """
        from anthropic import AsyncAnthropic  # Import the async client from Anthropic SDK
        return AsyncAnthropic(api_key=self.api_key)

    @staticmethod
    def build_expressive_prompt(character_description: str) -> str:
        """
        Constructs and returns a prompt based on the provided character description.
        This prompt instructs Claude to generate expressive dialogue that aligns semantically
        with the character's voice qualities and persona, optimized for TTS synthesis.

        Args:
            character_description (str): A description of the character's voice and persona.

        Returns:
            str: The prompt to be passed to the Anthropic API.
        """
        return f"""
        Character Description: {character_description}

        Please generate a short monologue (100-300 characters) that this character would naturally say.
        The dialogue should:

        - Match the speaking style, vocabulary, and emotional tone described in the character description
        - Include appropriate speech patterns, pauses, and vocal mannerisms mentioned in the description
        - Feel authentic to the character's background and situational context
        - Express a complete thought with a clear beginning and end
        - Use only standard punctuation (periods, commas, Em dashes, exclamation points, ellipses, question marks)
        - Avoid quotation marks, parentheses, asterisks, or special formatting
        - Emulate a highly characteristic, climactic, or emotional scene or line the character might reasonably deliver
        - Be at least 100 characters but not exceed 300 characters in length

        Examples of matching speaking style:
        - If the character is a pirate then use language like "arr," "ye," and other things pirates say.
        - If the character is a surfer then use language like "far out," "righteous," and other things surfers say.

        Emotional text should be inserted where context-appropriate and in-character. Here are some examples of
        emotional text:
        - "Oh god... Malcolm, please come back to us!"
        = "Mmm... It's like candy... Oh my god, it's so good..."
        - "Ugh, she gets everything. I wish I could just, like, have her life for one day."
        - "My god... what have you done... How could you do this..."
        - "Woah... it's so beautiful... and I feel so small..."
        - "I am so happy, woohoo, this is the greatest! I'm celebrating, and, like, so excited to be here with all of
        you. Yay!"
        - "Oh gosh, um, I didn't mean for that to happen. I hope I didn't, like, make things too awkward. Sorry, I
        tend to be clumsy, y'know?"
        - "Oh god... oh no... get that away from me! Get it away!"
        - "I am beyond livid right now! Like someone actually thought this was an acceptable solution!"
        - "Oh, fantastic, another meeting that could've been an email... I'm just thrilled to be here."
        - "OH, NAH, NOT ME, MATE—I'VE SEEN ENOUGH! GET IT AWAY! BLOODY 'ELL, JESUS!"

        Respond ONLY with the dialogue itself. Do not include any explanations, quotation marks,
        or additional context.
        """


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
        self.original_exception = original_exception
        self.message = message


@retry(
    retry=retry_if_exception(lambda e: not isinstance(e, UnretryableAnthropicError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=5),
    before=before_log(logger, logging.DEBUG),
    after=after_log(logger, logging.DEBUG),
    reraise=True,
)
async def generate_text_with_claude(character_description: str, config: Config) -> str:
    """
    Asynchronously generates text using Claude (Anthropic LLM) via the asynchronous Anthropic SDK.

    This function includes retry logic and error translation. It raises a custom
    UnretryableAnthropicError for unretryable API errors and AnthropicError for other errors.

    Args:
        character_description (str): The input character description.
        config (Config): Application configuration including Anthropic settings.

    Returns:
        str: The generated text.

    Raises:
        UnretryableAnthropicError: For unretryable API errors.
        AnthropicError: For other errors communicating with the Anthropic API.
    """
    try:
        anthropic_config = config.anthropic_config
        prompt = anthropic_config.build_expressive_prompt(character_description)
        logger.debug(f"Generating text with Claude. Character description length: {len(prompt)} characters.")

        assert anthropic_config.system_prompt is not None, "system_prompt must be set."

        response: Message = await anthropic_config.client.messages.create(
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

    except APIError as e:
        logger.error(f"Anthropic API request failed: {e!s}")
        clean_message = _extract_anthropic_error_message(e)

        if (
            hasattr(e, 'status_code')
            and e.status_code is not None
            and CLIENT_ERROR_CODE <= e.status_code < SERVER_ERROR_CODE
        ):
            raise UnretryableAnthropicError(message=clean_message, original_exception=e) from e

        raise AnthropicError(message=clean_message, original_exception=e) from e

    except Exception as e:
        error_type = type(e).__name__
        error_message = str(e) if str(e) else f"An error of type {error_type} occurred"
        logger.error(f"Error during Anthropic API call: {error_type} - {error_message}")
        clean_message = "An unexpected error occurred while processing your request. Please try again later."

        raise AnthropicError(message=clean_message, original_exception=e) from e


def _extract_anthropic_error_message(e: APIError) -> str:
    """
    Extracts a clean, user-friendly error message from an Anthropic API error response.

    Args:
        e (APIError): The Anthropic API error exception containing response information.

    Returns:
        str: A clean, user-friendly error message suitable for display to end users.
    """
    clean_message = GENERIC_API_ERROR_MESSAGE

    if hasattr(e, 'body') and isinstance(e.body, dict):
        error_body = e.body
        if (
            'error' in error_body
            and isinstance(error_body['error'], dict)
            and 'message' in error_body['error']
        ):
            clean_message = error_body['error']['message']

    return clean_message

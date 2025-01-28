"""
utils.py

This file contains utility functions that are shared across the project.
These functions provide reusable logic to simplify code in other modules.

Key Features:
- Validates that required environment variables are set, raising meaningful errors otherwise.
- Provides helper functions for text validation and truncation.

Functions:
- truncate_text: Truncates a string to a specified length with ellipses.
- validate_env_var: Ensures the presence of a specific environment variable and retrieves its value.
- validate_prompt_length: Ensures that a prompt does not exceed the specified maximum length.
"""

# Standard Library Imports
import os
# Local Application Imports
from src.config import logger


def truncate_text(text: str, max_length: int = 50) -> str:
    """
    Truncate a string to the specified length, appending ellipses if necessary.

    Args:
        text (str): The text to truncate.
        max_length (int): The maximum length of the truncated string.

    Returns:
        str: The truncated text.

    Examples:
        >>> truncate_text("Hello, World!", 5)
        'Hello...'
        >>> truncate_text("Short string", 20)
        'Short string'
        >>> truncate_text("Edge case with zero length", 0)
        ''
    """
    if max_length <= 0:
        logger.warning(f"Invalid max_length={max_length}. Returning empty string.")
        return ""

    is_truncated = len(text) > max_length
    if is_truncated:
        logger.debug(f"Truncated text to {max_length} characters.")
    
    return text[:max_length] + ("..." if is_truncated else "")


def validate_env_var(var_name: str) -> str:
    """
    Validates that an environment variable is set and returns its value.

    Args:
        var_name (str): The name of the environment variable to validate.

    Returns:
        str: The value of the environment variable.

    Raises:
        ValueError: If the environment variable is not set.
    
    Examples:
        >>> import os
        >>> os.environ["EXAMPLE_VAR"] = "example_value"
        >>> validate_env_var("EXAMPLE_VAR")
        'example_value'

        >>> validate_env_var("MISSING_VAR")
        Traceback (most recent call last):
          ...
        ValueError: MISSING_VAR is not set. Please ensure it is defined in your environment variables.
    """
    value = os.environ.get(var_name, "")
    if not value:
        raise ValueError(f"{var_name} is not set. Please ensure it is defined in your environment variables.")
    return value


def validate_prompt_length(prompt: str, max_length: int, min_length: int) -> None:
    """
    Validates that a prompt is within specified minimum and maximum length limits.

    Args:
        prompt (str): The input prompt to validate.
        max_length (int): The maximum allowed length for the prompt.
        min_length (int): The minimum required length for the prompt.

    Raises:
        ValueError: If the prompt is empty, too short, or exceeds max_length.

    Example:
        >>> validate_prompt_length("Hello world", max_length=500, min_length=5)
        # Passes validation

        >>> validate_prompt_length("", max_length=500, min_length=1)
        # Raises ValueError: "Prompt must be at least 1 character(s) long."
    """
    logger.debug(f"Prompt length being validated: {len(prompt)} characters")

    # Check if prompt is empty or too short
    stripped_prompt = prompt.strip()
    if len(stripped_prompt) < min_length:
        raise ValueError(
            f"Prompt must be at least {min_length} character(s) long. "
            f"Received only {len(stripped_prompt)}."
        )

    # Check if prompt is too long
    if len(stripped_prompt) > max_length:
        raise ValueError(
            f"The prompt exceeds the maximum allowed length of {max_length} characters. "
            f"Your prompt contains {len(stripped_prompt)} characters."
        )

    logger.debug(f"Prompt length validation passed for prompt: {truncate_text(stripped_prompt)}")
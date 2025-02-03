"""
types.py

This module defines custom types for the application to enforce the structure
of the options map used in the user interface. This ensures that each option
has a consistent structure including both the provider and the associated voice.
"""

from typing import TypedDict, Literal, Dict


TTSProviderName = Literal["Hume AI", "ElevenLabs", "Unknown"]
"""TTSProviderName represents the allowed provider names for TTS services."""


class OptionDetails(TypedDict):
    """
    A typed dictionary representing the details of an option.

    Attributes:
        provider (TTSProviderName): The name of the provider (either 'Hume AI' or 'ElevenLabs').
        voice (str): The name of the voice associated with the option.
    """

    provider: TTSProviderName
    voice: str


OptionKey = Literal["Option A", "Option B"]
"""OptionKey is restricted to the literal values 'Option A' or 'Option B'."""


OptionMap = Dict[OptionKey, OptionDetails]
"""OptionMap defines the structure of the options mapping, where each key is an OptionKey
and the value is an OptionDetails dictionary."""

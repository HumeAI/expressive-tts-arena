"""
types.py

This module defines custom types for the application to enforce the structure
of the options map used in the user interface. This ensures that each option
has a consistent structure including both the provider and the associated voice.
"""

from typing import TypedDict, Literal, Dict


TTSProviderName = Literal["Hume AI", "ElevenLabs"]
"""TTSProviderName represents the allowed provider names for TTS services."""


OptionKey = Literal["Option A", "Option B"]
"""OptionKey is restricted to the literal values 'Option A' or 'Option B'."""


OptionMap = Dict[OptionKey, TTSProviderName]
"""OptionMap defines the structure of the options mapping, where each key is an OptionKey
and the value is an OptionDetails dictionary."""

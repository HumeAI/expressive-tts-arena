"""
types.py

This module defines custom types for the application.
"""

# Standard Library Imports
from typing import Dict, Literal, TypedDict


TTSProviderName = Literal["Hume AI", "ElevenLabs"]
"""TTSProviderName represents the allowed provider names for TTS services."""


ComparisonType = Literal["Hume AI - Hume AI", "Hume AI - ElevenLabs"]
"""Comparison type denoting which providers are compared."""


OptionKey = Literal["Option A", "Option B"]
"""OptionKey is restricted to the literal values 'Option A' or 'Option B'."""


OptionMap = Dict[OptionKey, TTSProviderName]
"""OptionMap defines the structure of the options mapping, where each key is an OptionKey and the value is a TTS provider."""


class VotingResults(TypedDict):
    """Voting results data structure representing values we want to persist to the votes DB"""

    comparison_type: str
    winning_provider: TTSProviderName
    winning_option: OptionKey
    option_a_provider: TTSProviderName
    option_b_provider: TTSProviderName
    option_a_generation_id: str
    option_b_generation_id: str
    voice_description: str
    text: str
    is_custom_text: bool

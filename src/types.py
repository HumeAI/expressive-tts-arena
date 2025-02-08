"""
types.py

This module defines custom types for the application.
"""

# Standard Library Imports
from typing import Dict, Literal, NamedTuple, TypedDict


TTSProviderName = Literal["Hume AI", "ElevenLabs"]
"""TTSProviderName represents the allowed provider names for TTS services."""


ComparisonType = Literal["Hume AI - Hume AI", "Hume AI - ElevenLabs"]
"""Comparison type denoting which providers are compared."""


OptionKey = Literal["Option A", "Option B"]
"""OptionKey is restricted to the literal values 'Option A' or 'Option B'."""


OptionMap = Dict[OptionKey, TTSProviderName]
"""OptionMap defines the structure of the options mapping, where each key is an OptionKey and the value is a TTS provider."""


class Option(NamedTuple):
    """
    Represents a text-to-speech generation option.

    This type encapsulates the details for a generated text-to-speech (TTS) option,
    including the provider that produced the audio, the relative file path to the generated
    audio file, and the unique generation identifier associated with the TTS output.

    Attributes:
        provider (TTSProviderName): The TTS provider that generated the audio.
        audio (str): The relative file path to the audio file produced by the TTS provider.
        generation_id (str): The unique identifier for this TTS generation.
    """

    provider: TTSProviderName
    audio: str
    generation_id: str


class VotingResults(TypedDict):
    """Voting results data structure representing values we want to persist to the votes DB"""

    comparison_type: ComparisonType
    winning_provider: TTSProviderName
    winning_option: OptionKey
    option_a_provider: TTSProviderName
    option_b_provider: TTSProviderName
    option_a_generation_id: str
    option_b_generation_id: str
    voice_description: str
    text: str
    is_custom_text: bool

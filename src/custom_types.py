"""
custom_types.py

This module defines custom types for the application.
"""

# Standard Library Imports
from typing import Literal, NamedTuple, Optional, TypedDict

TTSProviderName = Literal["Hume AI", "ElevenLabs"]
"""TTSProviderName represents the allowed provider names for TTS services."""


ComparisonType = Literal["Hume AI - Hume AI", "Hume AI - ElevenLabs"]
"""Comparison type denoting which providers are compared."""


OptionLabel = Literal["Option A", "Option B"]
"""OptionLabel is restricted to the literal values 'Option A' or 'Option B'."""


OptionKey = Literal["option_a", "option_b"]
"""OptionKey is restricted to the literal values 'option_a' or 'option_b'."""


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
    option_a_generation_id: Optional[str]
    option_b_generation_id: Optional[str]
    character_description: str
    text: str
    is_custom_text: bool


class OptionDetail(TypedDict):
    """
    Details for a single TTS option.

    Attributes:
        provider (TTSProviderName): The TTS provider that generated the audio.
        generation_id (Optional[str]): The unique identifier for this TTS generation, or None if not available.
        audio_file_path (str): The relative file path to the generated audio file.
    """

    provider: TTSProviderName
    generation_id: Optional[str]
    audio_file_path: str


class OptionMap(TypedDict):
    """
    Mapping of TTS options.

    Structure:
        option_a: OptionDetail,
        option_b: OptionDetail
    """

    option_a: OptionDetail
    option_b: OptionDetail

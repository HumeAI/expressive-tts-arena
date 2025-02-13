"""
constants.py

This module defines global constants used throughout the project.
"""

# Standard Library Imports
from typing import List

# Third-Party Library Imports
from src.custom_types import ComparisonType, OptionKey, OptionLabel, TTSProviderName

CLIENT_ERROR_CODE = 400
SERVER_ERROR_CODE = 500

# UI constants
HUME_AI: TTSProviderName = "Hume AI"
ELEVENLABS: TTSProviderName = "ElevenLabs"
TTS_PROVIDERS: List[TTSProviderName] = ["Hume AI", "ElevenLabs"]

HUME_TO_HUME: ComparisonType = "Hume AI - Hume AI"
HUME_TO_ELEVENLABS: ComparisonType = "Hume AI - ElevenLabs"

CHARACTER_DESCRIPTION_MIN_LENGTH: int = 20
CHARACTER_DESCRIPTION_MAX_LENGTH: int = 800

OPTION_A_KEY: OptionKey = "option_a"
OPTION_B_KEY: OptionKey = "option_b"
OPTION_A_LABEL: OptionLabel = "Option A"
OPTION_B_LABEL: OptionLabel = "Option B"
TROPHY_EMOJI: str = "🏆"
SELECT_OPTION_A: str = "Select Option A"
SELECT_OPTION_B: str = "Select Option B"


# A collection of pre-defined character descriptions categorized by theme, used to provide users with
# inspiration for generating creative text for expressive TTS, and generating novel voices.
SAMPLE_CHARACTER_DESCRIPTIONS: dict = {
    "🚀 Stranded Astronaut": (
        "A lone astronaut whose voice mirrors the silent vastness of space—a low, steady tone imbued "
        "with isolation and quiet wonder. It carries the measured resolve of someone sending a final "
        "transmission, with an undercurrent of wistful melancholy."
    ),
    "📜 Timeless Poet": (
        "An ageless poet with a voice that flows like gentle verse—a soft, reflective tone marked by "
        "deliberate pauses. It speaks with the measured cadence of classic sonnets, evoking both the "
        "fragile beauty of time and heartfelt introspection."
    ),
    "🐱 Whimsical Feline": (
        "A mischievous cat whose voice is playful yet mysterious—light, quick-witted, and infused with "
        "an enchanting purr. It hints at secret adventures and hidden charm, balancing exuberance with "
        "a subtle, smooth allure."
    ),
    "🔥 Revolutionary Orator": (
        "A defiant orator whose voice builds from quiet determination to passionate fervor—a clear, "
        "commanding tone that resonates with conviction. It starts measured and resolute, then rises "
        "to a crescendo of fervor, punctuated by deliberate pauses that emphasize each rallying cry."
    ),
    "👻 Haunted Keeper": (
        "A solitary lighthouse keeper with a voice that carries the weight of forgotten storms—a soft, "
        "measured tone with an echo of sorrow. It speaks as if whispering long-held secrets in the dark, "
        "blending quiet melancholy with an air of enduring mystery."
    ),
}

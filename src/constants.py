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

# other characters
# Surfer dude
# Meditation guru / ASMR
# British nature documentarian
# Pirate captain
# Victorian ghost story storyteller
# Texan woman (folksy style)
# Stranded astronaut
# Film noir narrator

# A collection of pre-defined character descriptions categorized by theme, used to provide users with
# inspiration for generating creative, expressive text inputs for TTS, and generating novel voices.
SAMPLE_CHARACTER_DESCRIPTIONS: dict = {
    "🏄 Surfer Dude": (
        "A laid-back surfer with a voice that flows like ocean waves—a mellow, easygoing tone infused "
        "with sun-soaked warmth. It carries the rhythmic cadence of breaking surf, punctuated by "
        "carefree laughter and an infectious enthusiasm for life's simple pleasures."
    ),
    "🧘 Meditation Guru": (
        "A serene meditation guide whose voice is a gentle stream of tranquility—soft, measured tones "
        "that float like incense smoke. Each word emerges with mindful intention, creating a soothing "
        "atmosphere of peace and present-moment awareness."
    ),
    "🌿 British Naturalist": (
        "A passionate nature documentarian with a voice that brings the wild to life—crisp, refined "
        "tones brimming with wonder and expertise. It shifts seamlessly from hushed observation to "
        "animated excitement, painting vivid pictures of the natural world's endless marvels."
    ),
    "🏴‍☠️ Pirate Captain": (
        "A weathered sea captain whose voice rumbles like distant thunder—rich, commanding tones "
        "seasoned by salt spray and adventure. It carries the weight of countless voyages, blending "
        "gruff authority with the playful spirit of a born storyteller."
    ),
    "🕯️ Victorian Ghost Storyteller": (
        "A mysterious raconteur whose voice weaves shadows into stories—velvet-dark tones that dance "
        "between whispers and dramatic flourishes. It draws listeners close with elegant phrasing, "
        "building tension through perfectly timed pauses and haunting inflections."
    ),
    "🌟 Texan Storyteller": (
        "A warm-hearted Texan woman whose voice carries the spirit of wide-open skies—honeyed tones "
        "rich with folksy wisdom and charm. It wraps around words like a comfortable quilt, sharing "
        "tales with the unhurried grace of a front-porch conversation."
    ),
    "🚀 Stranded Astronaut": (
        "A lone astronaut whose voice mirrors the silent vastness of space—a low, steady tone imbued "
        "with isolation and quiet wonder. It carries the measured resolve of someone sending a final "
        "transmission, with an undercurrent of wistful melancholy."
    ),
    "🎬 Noir Narrator": (
        "A hardboiled detective whose voice cuts through darkness like neon on wet streets—sharp, "
        "world-weary tones dripping with cynical wit. It paints pictures in shades of gray, each word "
        "chosen with the precision of a private eye piecing together clues."
    ),
}

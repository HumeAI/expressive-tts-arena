"""
constants.py

This module defines global constants used throughout the project.
"""

# Standard Library Imports
from typing import List

# Third-Party Library Imports
from src.common.common_types import (
    ComparisonType,
    OptionKey,
    TTSProviderName,
)

CLIENT_ERROR_CODE = 400
SERVER_ERROR_CODE = 500
RATE_LIMIT_ERROR_CODE = 429

HUME_AI: TTSProviderName = "Hume AI"
ELEVENLABS: TTSProviderName = "ElevenLabs"
OPENAI: TTSProviderName = "OpenAI"

TTS_PROVIDERS: List[TTSProviderName] = ["Hume AI", "OpenAI", "ElevenLabs"]
TTS_PROVIDER_LINKS = {
    "Hume AI": {
        "provider_link": "https://hume.ai/",
        "model_link": "https://www.hume.ai/blog/octave-the-first-text-to-speech-model-that-understands-what-its-saying"
    },
    "ElevenLabs": {
        "provider_link": "https://elevenlabs.io/",
        "model_link": "https://elevenlabs.io/blog/rvg",
    },
    "OpenAI": {
        "provider_link": "https://openai.com/",
        "model_link": "https://platform.openai.com/docs/models/gpt-4o-mini-tts",
    }
}

HUME_TO_HUME: ComparisonType = "Hume AI - Hume AI"
HUME_TO_ELEVENLABS: ComparisonType = "Hume AI - ElevenLabs"
HUME_TO_OPENAI: ComparisonType = "Hume AI - OpenAI"
OPENAI_TO_ELEVENLABS: ComparisonType = "OpenAI - ElevenLabs"

CHARACTER_DESCRIPTION_MIN_LENGTH: int = 20
CHARACTER_DESCRIPTION_MAX_LENGTH: int = 400

TEXT_MIN_LENGTH: int = 100
TEXT_MAX_LENGTH: int = 400

OPTION_A_KEY: OptionKey = "option_a"
OPTION_B_KEY: OptionKey = "option_b"

SELECT_OPTION_A: str = "Select Option A"
SELECT_OPTION_B: str = "Select Option B"

GENERIC_API_ERROR_MESSAGE: str = "An unexpected error occurred while processing your request. Please try again shortly."

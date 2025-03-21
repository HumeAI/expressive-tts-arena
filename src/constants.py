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
CHARACTER_DESCRIPTION_MAX_LENGTH: int = 1000

TEXT_MIN_LENGTH: int = 100
TEXT_MAX_LENGTH: int = 1000

OPTION_A_KEY: OptionKey = "option_a"
OPTION_B_KEY: OptionKey = "option_b"
OPTION_A_LABEL: OptionLabel = "Option A"
OPTION_B_LABEL: OptionLabel = "Option B"

TROPHY_EMOJI: str = "🏆"

SELECT_OPTION_A: str = "Select Option A"
SELECT_OPTION_B: str = "Select Option B"

# A collection of pre-defined character descriptions categorized by theme, used to provide users with
# inspiration for generating creative, expressive text inputs for TTS, and generating novel voices.
SAMPLE_CHARACTER_DESCRIPTIONS: dict = {
    "🦘 Australian Naturalist": (
        "The speaker has a contagiously enthusiastic Australian accent, with the relaxed, sun-kissed vibe of a "
        "wildlife expert fresh off the outback, delivering an amazing, laid-back narration."
    ),
    "🧘 Meditation Guru": (
        "A mindfulness instructor with a gentle, soothing voice that flows at a slow, measured pace with natural "
        "pauses. Their consistently calm, low-pitched tone has minimal variation, creating a peaceful auditory "
        "experience."
    ),
    "🚀 Stranded Astronaut": (
        "An astronaut in deep space communicating with a clear, precise voice with subtle radio distortion. "
        "Speaking with controlled emotion, technical accuracy, measured pacing and thoughtful silences."
    ),
    "🎬 Noir Detective": (
        "A 1940s private investigator narrating with a gravelly voice and deliberate pacing. "
        "Speaks with a cynical, world-weary tone that drops lower when delivering key observations."
    ),
    "🕯️ Victorian Ghost Storyteller": (
        "A Victorian-era raconteur speaking with a refined English accent and formal, precise diction. Voice "
        "modulates between hushed, tense whispers and dramatic declarations when describing eerie occurrences."
    ),
    "🌿 English Naturalist": (
        "A wildlife documentarian speaking with a crisp, articulate English accent and clear enunciation. Voice "
        "alternates between hushed, excited whispers and enthusiastic explanations filled with genuine wonder."
    ),
    "🌟 Texan Storyteller": (
        "A speaker from rural Texas speaking with a warm voice and distinctive Southern drawl featuring elongated "
        "vowels. Talks unhurriedly with a musical quality and occasional soft laughter."
    ),
    "🏄 Chill Surfer": (
        "A California surfer talking with a casual, slightly nasal voice and laid-back rhythm. Uses rising "
        "inflections at sentence ends and bursts into spontaneous laughter when excited."
    ),
    "📢 Old-School Radio Announcer": (
        "The speaker has the voice of a seasoned horse race announcer, with a booming, energetic voice, "
        "a touch of old-school radio charm, and the enthusiastic delivery of a viral commentator."
    ),
    "👑 Obnoxious Royal": (
        "A member of the English royal family speaks in a smug and authoritative voice in an obnoxious, proper "
        "English accent. They are insecure, arrogant, and prone to tantrums."
    ),
    "🏰 Medieval Peasant": (
        "A film portrayal of a medieval peasant speaking with a thick cockney accent and a worn voice, "
        "dripping with sarcasm and self-effacing humor."
    ),
}

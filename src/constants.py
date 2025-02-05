"""
constants.py

This module defines global constants used throughout the project.
"""

from src.types import OptionKey, TTSProviderName

# UI constants
HUME_AI: TTSProviderName = "Hume AI"
ELEVENLABS: TTSProviderName = "ElevenLabs"
UNKNOWN_PROVIDER: TTSProviderName = "Unknown"

PROMPT_MIN_LENGTH: int = 10
PROMPT_MAX_LENGTH: int = 400

OPTION_A: OptionKey = "Option A"
OPTION_B: OptionKey = "Option B"
TROPHY_EMOJI: str = "🏆"
VOTE_FOR_OPTION_A: str = "Vote for option A"
VOTE_FOR_OPTION_B: str = "Vote for option B"


# A collection of pre-defined prompts categorized by theme, used to provide users with
# inspiration for generating creative text for expressive TTS.
SAMPLE_PROMPTS: dict = {
    "🚀 Dramatic Monologue (Stranded Astronaut)": (
        "Create a poignant final transmission from a lone astronaut on Mars to mission control. "
        "Voice: low, measured pace, with subtle tremors of emotion. Content should move from "
        "awe-struck description of the Martian sunset to peaceful acceptance. Include natural "
        "pauses for emotional weight. Keep the tone intimate and contemplative, as if speaking "
        "softly into a radio mic. End with dignified finality."
    ),
    "📜 Poetic Sonnet (The Passage of Time)": (
        "Craft a sonnet about time's flow, suitable for measured, resonant delivery. "
        "Voice: clear, rhythmic, with careful emphasis on key metaphors. Flow from quiet "
        "reflection to profound realization. Include strategic pauses between quatrains. "
        "Balance crisp consonants with flowing vowels for musical quality. Maintain consistent "
        "meter for natural speech rhythm."
    ),
    "🐱 Whimsical Children's Story (Talking Cat)": (
        "Tell a playful tale of a curious cat's magical library adventure. "
        "Voice: bright, energetic, with clear character distinctions. Mix whispered "
        "conspiracies with excited discoveries. Include dramatic pauses for suspense "
        "and giggles. Use bouncy rhythm for action scenes, slower pace for wonder. "
        "End with warm, gentle closure perfect for bedtime."
    ),
    "🔥 Intense Speech (Freedom & Justice)": (
        "Deliver a rousing resistance speech that builds from quiet determination to powerful resolve. "
        "Voice: start controlled and intense, rise to passionate crescendo. Include strategic "
        "pauses for impact. Mix shorter, punchy phrases with flowing calls to action. "
        "Use strong consonants and open vowels for projection. End with unshakeable conviction."
    ),
    "👻 Mysterious Horror Scene (Haunted Lighthouse)": (
        "Narrate a spine-chilling lighthouse encounter that escalates from unease to revelation. "
        "Voice: hushed, tense, with subtle dynamic range. Mix whispers with clearer tones. "
        "Include extended pauses for tension. Use sibilants and soft consonants for "
        "atmospheric effect. Build rhythm with the lighthouse's beam pattern. End with haunting "
        "revelation."
    ),
}

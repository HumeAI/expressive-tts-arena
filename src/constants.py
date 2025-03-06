"""
constants.py

This module defines global constants used throughout the project.
"""

# Standard Library Imports
from typing import Dict, List

# Third-Party Library Imports
from src.custom_types import ComparisonType, OptionKey, OptionLabel, TTSProviderName

CLIENT_ERROR_CODE = 400
SERVER_ERROR_CODE = 500
RATE_LIMIT_ERROR_CODE = 429


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

GENERIC_API_ERROR_MESSAGE: str = "An unexpected error occurred while processing your request. Please try again shortly."

# A collection of pre-defined character descriptions categorized by theme, used to provide users with
# inspiration for generating creative, expressive text inputs for TTS, and generating novel voices.
SAMPLE_CHARACTER_DESCRIPTIONS: dict = {
    "🧘 Meditation Guru": (
        "The speaker is a mindfulness instructor with a gentle, soothing voice that flows at a slow, measured pace "
        "with natural pauses. Their consistently calm, low-pitched tone has minimal variation, creating a peaceful "
        "auditory experience."
    ),
    "🎬 Noir Detective": (
        "A noir film portrayal of a 1940s private investigator narrating with a low, gravelly voice and deliberate "
        "pacing. Speaks with a cynical, world-weary tone that drops lower when delivering key observations."
    ),
    "🕯️ Victorian Ghost Storyteller": (
        "The speaker is a Victorian-era raconteur speaking with a refined British accent and formal, precise diction. "
        "Voice modulates between hushed, tense whispers and dramatic declarations when describing eerie occurrences."
    ),
    "🌿 British Naturalist": (
        "Speaker is a wildlife documentarian speaking with a crisp, articulate British accent and clear enunciation. "
        "Voice alternates between hushed, excited whispers and enthusiastic explanations filled with genuine wonder."
    ),
    "🌟 Texan Storyteller": (
        "The speaker is a woman from rural Texas speaking with a warm voice and distinctive Southern drawl featuring "
        "elongated vowels. Talks unhurriedly with a musical quality and occasional soft laughter."
    ),
    "🏄 Surfer Dude": (
        "The speaker is a California surfer talking with a casual, slightly nasal voice and laid-back rhythm. Uses "
        "rising inflections at sentence ends and bursts into spontaneous laughter when excited."
    ),
    "👑 Obnoxious Prince": (
        "Speaker is a prince of England who speaks in a smug and authoritative voice in an obnoxious, proper English "
        "accent. He is insecure, arrogant, and prone to tantrums."
    ),
    "🏰 Medieval Peasant Man": (
        "A film portrayal of a medieval peasant speaking with a thick cockney accent and a worn voice, dripping with "
        "sarcasm and self-effacing humor."
    ),
}


# HTML and social media metadata for the Gradio application
# These tags define SEO-friendly content and provide rich previews when shared on social platforms
META_TAGS: List[Dict[str, str]] = [
    # HTML Meta Tags (description)
    {
        'name': 'description',
        'content': 'An open-source web application for comparing and evaluating the expressiveness of different text-to-speech models, including Hume AI and ElevenLabs.'
    },
    # Facebook Meta Tags
    {
        'property': 'og:url',
        'content': 'https://hume.ai'
    },
    {
        'property': 'og:type',
        'content': 'website'
    },
    {
        'property': 'og:title',
        'content': 'Expressive TTS Arena'
    },
    {
        'property': 'og:description',
        'content': 'An open-source web application for comparing and evaluating the expressiveness of different text-to-speech models, including Hume AI and ElevenLabs.'
    },
    {
        'property': 'og:image',
        'content': '/static/arena-opengraph-logo.png'
    },
    # Twitter Meta Tags
    {
        'name': 'twitter:card',
        'content': 'summary_large_image'
    },
    {
        'property': 'twitter:domain',
        'content': 'hume.ai'
    },
    {
        'property': 'twitter:url',
        'content': 'https://hume.ai'
    },
    {
        'name': 'twitter:creator',
        'content': '@hume_ai'
    },
    {
        'name': 'twitter:title',
        'content': 'Expressive TTS Arena'
    },
    {
        'name': 'twitter:description',
        'content': 'An open-source web application for comparing and evaluating the expressiveness of different text-to-speech models, including Hume AI and ElevenLabs.'
    },
    {
        'name': 'twitter:image',
        'content': '/static/arena-opengraph-logo.png'
    }
]

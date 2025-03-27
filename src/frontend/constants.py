"""
constants.py

This module defines constants used in the UI.
"""

# Third-Party Library Imports
from src.common.common_types import OptionLabel

OPTION_A_LABEL: OptionLabel = "Option A"
OPTION_B_LABEL: OptionLabel = "Option B"

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
    "🎬 Noir Detective": (
        "A 1940s private investigator narrating with a gravelly voice and deliberate pacing. "
        "Speaks with a cynical, world-weary tone that drops lower when delivering key observations."
    ),
    "🕯️ Victorian Ghost Storyteller": (
        "The speaker is a Victorian-era raconteur speaking with a refined English accent and formal, precise diction. Voice "
        "modulates between hushed, tense whispers and dramatic declarations when describing eerie occurrences."
    ),
    "🌿 English Naturalist": (
        "Speaker is a wildlife documentarian speaking with a crisp, articulate English accent and clear enunciation. Voice "
        "alternates between hushed, excited whispers and enthusiastic explanations filled with genuine wonder."
    ),
    "🌟 Texan Storyteller": (
        "A speaker from rural Texas speaking with a warm voice and distinctive Southern drawl featuring elongated "
        "vowels. Talks unhurriedly with a musical quality and occasional soft laughter."
    ),
    "🏄 Chill Surfer": (
        "The speaker is a California surfer talking with a casual, slightly nasal voice and laid-back rhythm. Uses rising "
        "inflections at sentence ends and bursts into spontaneous laughter when excited."
    ),
    "📢 Old-School Radio Announcer": (
        "The speaker has the voice of a seasoned horse race announcer, with a booming, energetic voice, a touch of "
        "old-school radio charm, and the enthusiastic delivery of a viral commentator."
    ),
    "👑 Obnoxious Royal": (
        "Speaker is a member of the English royal family speaks in a smug and authoritative voice in an obnoxious, proper "
        "English accent. They are insecure, arrogant, and prone to tantrums."
    ),
    "🏰 Medieval Peasant": (
        "A film portrayal of a medieval peasant speaking with a thick cockney accent and a worn voice, "
        "dripping with sarcasm and self-effacing humor."
    ),
}

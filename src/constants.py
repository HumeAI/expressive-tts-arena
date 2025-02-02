"""
constants.py

This module defines global constants used throughout the project.
"""

# UI constants
HUME_AI: str = 'Hume'
ELEVENLABS: str = 'ElevenLabs'
UNKNOWN_PROVIDER: str = 'Unknown'

PROMPT_MIN_LENGTH: int = 10
PROMPT_MAX_LENGTH: int = 400

OPTION_A: str = 'Option A'
OPTION_B: str = 'Option B'
TROPHY_EMOJI: str = '🏆'
VOTE_FOR_OPTION_A: str = 'Vote for option A'
VOTE_FOR_OPTION_B: str = 'Vote for option B'


# A collection of pre-defined prompts categorized by theme, used to provide users with 
# inspiration for generating creative text for expressive TTS.
SAMPLE_PROMPTS: dict = {
    '🚀 Dramatic Monologue (Stranded Astronaut)': 
        'Write a short dramatic monologue from a lone astronaut stranded on Mars, speaking to '
        'mission control for the last time. The tone should be reflective and filled with awe, conveying '
        'resignation and finality. Describe the Martian landscape and their thoughts in a way that '
        'would evoke emotion and depth.',
    
    '📜 Poetic Sonnet (The Passage of Time)': 
        'Compose a concise sonnet about the passage of time, using vivid imagery and a flowing, '
        'melodic rhythm. The poem should evoke the contrast between fleeting moments and eternity, '
        'capturing both beauty and melancholy, with natural pacing for speech delivery.',
    
    "🐱 Whimsical Children's Story (Talking Cat)": 
        'Tell a short, whimsical bedtime story about a mischievous talking cat who sneaks into a grand '
        'wizard’s library at night and accidentally casts a spell that brings the books to life. Keep the '
        'tone playful and filled with wonder, ensuring the language flows smoothly.',
    
    '🔥 Intense Speech (Freedom & Justice)': 
        'Write a powerful, impassioned speech from a rebel leader rallying their people against a '
        'tyrant. The speech should be urgent, filled with conviction, and call for freedom and justice, '
        'making sure the emotional intensity is evident in the phrasing.',
    
    '👻 Mysterious Horror Scene (Haunted Lighthouse)': 
        'Describe a chilling ghostly encounter in an abandoned lighthouse on a foggy night. The '
        'protagonist, alone and cold, hears whispers from the shadows, telling them secrets they were '
        'never meant to know. Use language that builds suspense and tension, ensuring it sounds '
        'haunting and engaging.'
}
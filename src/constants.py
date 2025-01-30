"""
constants.py

This module defines global constants used throughout the project.
"""

# Minimum and maximum prompt length constraints
PROMPT_MIN_LENGTH: int = 10
PROMPT_MAX_LENGTH: int = 300

# A collection of pre-defined prompts categorized by theme, used to provide users with inspiration for generating creative text.
SAMPLE_PROMPTS = {
    '🚀 Dramatic Monologue (Stranded Astronaut)': 
        'Write a short dramatic monologue from a lone astronaut stranded on Mars, '
        'speaking to mission control for the last time. The tone should be reflective, '
        'filled with awe and resignation as they describe the Martian landscape and their final thoughts.',
    
    '📜 Poetic Sonnet (The Passage of Time)': 
        'Compose a sonnet about the passage of time, using vivid imagery and a flowing, melodic rhythm. '
        'The poem should contrast fleeting moments with eternity, capturing both beauty and melancholy.',
    
    "🐱 Whimsical Children's Story (Talking Cat)": 
        'Tell a short bedtime story about a mischievous talking cat who sneaks into a grand wizard’s library '
        'at night and accidentally casts a spell that brings the books to life. '
        'Make the tone playful, whimsical, and filled with wonder.',
    
    '🔥 Intense Speech (Freedom & Justice)': 
        'Write a powerful speech delivered by a rebel leader rallying their people against a tyrant. '
        'The speech should be passionate, filled with urgency and conviction, calling for freedom and justice.',
    
    '👻 Mysterious Horror Scene (Haunted Lighthouse)': 
        'Describe a chilling ghostly encounter in an abandoned lighthouse on a foggy night. '
        'The protagonist, alone and cold, begins hearing whispers from the shadows, '
        'telling them secrets they were never meant to know.'
}
# Standard Library Imports
import asyncio
import random
from typing import Tuple

# Local Application Imports
from src.common.common_types import Option, OptionMap, TTSProviderName
from src.common.config import Config, logger
from src.common.constants import ELEVENLABS, HUME_AI, OPENAI
from src.integrations import (
    text_to_speech_with_elevenlabs,
    text_to_speech_with_hume,
    text_to_speech_with_openai,
)


class TTSService:
    """
    Service for coordinating text-to-speech generation across different providers.

    This class handles the logic for selecting TTS providers, making concurrent API calls,
    and processing the responses into a unified format for the frontend.
    """

    def __init__(self, config: Config):
        """
        Initialize the TTS service with application configuration.

        Args:
            config (Config): Application configuration containing API settings
        """
        self.config = config
        self.tts_provider_functions = {
            HUME_AI: text_to_speech_with_hume,
            ELEVENLABS: text_to_speech_with_elevenlabs,
            OPENAI: text_to_speech_with_openai,
        }

    def __select_providers(self, text_modified: bool) -> Tuple[TTSProviderName, TTSProviderName]:
        """
        Select 2 TTS providers based on whether the text has been modified.

        Probabilities:
         - 50% HUME_AI, OPENAI
         - 25% OPENAI, ELEVENLABS
         - 20% HUME_AI, ELEVENLABS
         - 5% HUME_AI, HUME_AI

        If the `text_modified` argument is `True`, then 100% HUME_AI, HUME_AI

        Args:
            text_modified (bool): A flag indicating whether the text has been modified

        Returns:
            tuple: A tuple (TTSProviderName, TTSProviderName)
        """
        if text_modified:
            return HUME_AI, HUME_AI

        # When modifying the probability distribution, make sure the weights match the order of provider pairs
        provider_pairs = [
            (HUME_AI, OPENAI),
            (OPENAI, ELEVENLABS),
            (HUME_AI, ELEVENLABS),
            (HUME_AI, HUME_AI)
        ]
        weights = [0.5, 0.25, 0.2, 0.05]

        return random.choices(provider_pairs, weights=weights, k=1)[0]

    async def synthesize_speech(
        self,
        character_description: str,
        text: str,
        text_modified: bool
    ) -> OptionMap:
        """
        Generate speech for the given text using two different TTS providers.

        This method selects appropriate providers based on the text modification status,
        makes concurrent API calls to those providers, and returns the results.

        Args:
            character_description (str): Description of the character/voice for synthesis
            text (str): The text to synthesize into speech
            text_modified (bool): Whether the text has been modified from the original

        Returns:
            OptionMap: A mapping of shuffled TTS options, where each option includes
                    its provider, audio file path, and generation ID.
        """
        provider_a, provider_b = self.__select_providers(text_modified)

        logger.info(f"Starting speech synthesis with providers: {provider_a} and {provider_b}")

        task_a = self.tts_provider_functions[provider_a](character_description, text, self.config)
        task_b = self.tts_provider_functions[provider_b](character_description, text, self.config)

        (generation_id_a, audio_a), (generation_id_b, audio_b) = await asyncio.gather(task_a, task_b)

        logger.info(f"Synthesis succeeded for providers: {provider_a} and {provider_b}")

        option_a = Option(provider=provider_a, audio=audio_a, generation_id=generation_id_a)
        option_b = Option(provider=provider_b, audio=audio_b, generation_id=generation_id_b)

        options = [option_a, option_b]
        random.shuffle(options)
        shuffled_option_a, shuffled_option_b = options

        return {
            "option_a": {
                "provider": shuffled_option_a.provider,
                "generation_id": shuffled_option_a.generation_id,
                "audio_file_path": shuffled_option_a.audio,
            },
            "option_b": {
                "provider": shuffled_option_b.provider,
                "generation_id": shuffled_option_b.generation_id,
                "audio_file_path": shuffled_option_b.audio,
            },
        }

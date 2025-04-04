# Standard Library Imports
import asyncio
import random
import time
from typing import Tuple

# Third-Party Library Imports
import gradio as gr

# Local Application Imports
from src.common import constants
from src.common.common_types import OptionKey, OptionLabel, OptionMap
from src.common.config import Config, logger
from src.common.utils import submit_voting_results
from src.core import TTSService
from src.database import AsyncDBSessionMaker
from src.integrations import AnthropicError, ElevenLabsError, HumeError, OpenAIError, generate_text_with_claude

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

class Arena:
    def __init__(self, config: Config, db_session_maker: AsyncDBSessionMaker):
        self.config = config
        self.db_session_maker = db_session_maker
        self.tts_service = TTSService(config)

    def validate_input_length(
        self,
        input_value: str,
        min_length: int,
        max_length: int,
        input_name: str, # e.g., "character description", "text"
    ) -> None:
        """Validates input length against min/max limits."""
        stripped_value = input_value.strip()
        value_length = len(stripped_value)
        logger.debug(f"Validating length for '{input_name}': {value_length} characters")

        if value_length < min_length:
            raise ValueError(
                f"Your {input_name} is too short. Please enter at least "
                f"{min_length} characters. (Current length: {value_length})"
            )
        if value_length > max_length:
            raise ValueError(
                f"Your {input_name} is too long. Please limit it to "
                f"{max_length} characters. (Current length: {value_length})"
            )

    def validate_character_description_length(self, character_description: str) -> None:
        self.validate_input_length(
            character_description,
            constants.CHARACTER_DESCRIPTION_MIN_LENGTH,
            constants.CHARACTER_DESCRIPTION_MAX_LENGTH,
            "character description",
        )

    def validate_text_length(self, text: str) -> None:
        self.validate_input_length(
            text,
            constants.TEXT_MIN_LENGTH,
            constants.TEXT_MAX_LENGTH,
            "text",
        )

    async def generate_text(self, character_description: str) -> Tuple[gr.Textbox, str]:
        """
        Validates the character_description and generates text using Anthropic API.

        Args:
            character_description (str): The user-provided text for character description.

        Returns:
            Tuple containing:
              - The generated text update (as a dict from gr.update).
              - The generated text string.

        Raises:
            gr.Error: On validation or API errors.
        """
        try:
            self.validate_character_description_length(character_description)
        except ValueError as ve:
            logger.warning(f"Validation error: {ve}")
            raise gr.Error(str(ve))

        try:
            generated_text = await generate_text_with_claude(character_description, self.config)
            logger.info(f"Generated text ({len(generated_text)} characters).")
            return gr.update(value=generated_text), generated_text
        except AnthropicError as ae:
            logger.error(f"Text Generation Failed: AnthropicError while generating text: {ae!s}")
            raise gr.Error(f'There was an issue communicating with the Anthropic API: "{ae.message}"')
        except Exception as e:
            logger.error(f"Text Generation Failed: Unexpected error while generating text: {e!s}")
            raise gr.Error("Failed to generate text. Please try again shortly.")

    def warn_user_about_custom_text(self, text: str, generated_text: str) -> None:
        """
        Shows a warning to the user if they have modified the generated text.

        When users edit the generated text instead of using it as-is, only Hume Octave
        outputs will be generated for comparison rather than comparing against other
        providers. This function displays a warning to inform users of this limitation.

        Args:
            text (str): The current text that will be used for synthesis.
            generated_text (str): The original text that was generated by the system.

        Returns:
            None: This function displays a warning but does not return any value.
        """
        if text != generated_text:
            gr.Warning("When custom text is used, only Hume Octave outputs are generated.")

    async def synthesize_speech(
        self,
        character_description: str,
        text: str,
        generated_text_state: str,
    ) -> Tuple[gr.Audio, gr.Audio, OptionMap, bool, str, str, bool]:
        """
        Synthesizes two text-to-speech outputs, updates UI state components, and returns additional TTS metadata.

        This function generates TTS outputs using different providers based on the input text and its modification
        state.

        The outputs are processed and shuffled, and the corresponding UI components for two audio players are updated.
        Additional metadata such as the comparison type, generation IDs, and state information are also returned.

        Args:
            character_description (str): The description of the character used for generating the voice.
            text (str): The text content to be synthesized into speech.
            generated_text_state (str): The previously generated text state, used to determine if the text has
                                        been modified.

        Returns:
            Tuple containing:
                - gr.Audio: Update for the first audio player (with autoplay enabled).
                - gr.Audio: Update for the second audio player.
                - OptionMap: A mapping of option constants to their corresponding TTS providers.
                - bool: Flag indicating whether the text was modified.
                - str: The original text that was synthesized.
                - str: The original character description.
                - bool: Flag indicating whether the vote buttons should be enabled

        Raises:
            gr.Error: If any API or unexpected errors occur during the TTS synthesis process.
        """
        try:
            self.validate_character_description_length(character_description)
            self.validate_text_length(text)
        except ValueError as ve:
            logger.error(f"Validation error: {ve}")
            raise gr.Error(str(ve))

        try:
            text_modified = text != generated_text_state
            options_map: OptionMap = await self.tts_service.synthesize_speech(character_description, text, text_modified)

            return (
                gr.update(value=options_map["option_a"]["audio_file_path"], autoplay=True),
                gr.update(value=options_map["option_b"]["audio_file_path"]),
                options_map,
                text_modified,
                text,
                character_description,
                True,
            )
        except HumeError as he:
            logger.error(f"Synthesis failed with HumeError during TTS generation: {he!s}")
            raise gr.Error(f'There was an issue communicating with the Hume API: "{he.message}"')
        except OpenAIError as oe:
            logger.error(f"Synthesis failed with OpenAIError during TTS generation: {oe!s}")
            raise gr.Error(f'There was an issue communicating with the OpenAI API: "{oe.message}"')
        except ElevenLabsError as ee:
            logger.error(f"Synthesis failed with ElevenLabsError during TTS generation: {ee!s}")
            raise gr.Error(f'There was an issue communicating with the Elevenlabs API: "{ee.message}"')
        except Exception as e:
            logger.error(f"Synthesis failed with an unexpected error during TTS generation: {e!s}")
            raise gr.Error("An unexpected error occurred. Please try again shortly.")

    def determine_selected_option(self, selected_option_button: str) -> Tuple[OptionKey, OptionKey]:
        """
        Determines the selected option and the alternative option based on the user's selection.

        Args:
            selected_option_button (str): The option selected by the user, expected to be either
                constants.OPTION_A_KEY or constants.OPTION_B_KEY.

        Returns:
            tuple: A tuple (selected_option, other_option) where:
                - selected_option is the same as the selected_option.
                - other_option is the alternative option.
        """

        if selected_option_button == constants.SELECT_OPTION_A:
            selected_option, other_option = constants.OPTION_A_KEY, constants.OPTION_B_KEY
        elif selected_option_button == constants.SELECT_OPTION_B:
            selected_option, other_option = constants.OPTION_B_KEY, constants.OPTION_A_KEY
        else:
            raise ValueError(f"Invalid selected button: {selected_option_button}")

        return selected_option, other_option

    async def submit_vote(
        self,
        vote_submitted: bool,
        option_map: OptionMap,
        clicked_option_button: str,
        text_modified: bool,
        character_description: str,
        text: str,
    ) -> Tuple[
        bool,
        gr.Button,
        gr.Button,
        gr.Textbox,
        gr.Textbox,
        gr.Button
    ]:
        """
        Handles user voting and updates the UI to display vote results.

        Args:
            vote_submitted (bool): True if a vote was already submitted.
            option_map (OptionMap): A dictionary mapping option labels to their details.
            clicked_option_button (str): The button that was clicked.
            text_modified (bool): Whether the text was modified by the user.
            character_description (str): The character description.
            text (str): The text used for synthesis.

        Returns:
            A tuple of:
            - bool: A boolean indicating if the vote was accepted.
            - A dict update for hiding vote button A.
            - A dict update for hiding vote button B.
            - A dict update for showing vote result A textbox.
            - A dict update for showing vote result B textbox.
            - A dict update for enabling the synthesize speech button.
        """
        if not option_map or vote_submitted:
            return gr.skip(), gr.skip(), gr.skip(), gr.skip(), gr.skip(), gr.skip()

        selected_option, other_option = self.determine_selected_option(clicked_option_button)
        selected_provider = option_map[selected_option]["provider"]
        other_provider = option_map[other_option]["provider"]

        # Process vote in the background without blocking the UI
        asyncio.create_task(
            submit_voting_results(
                option_map,
                selected_option,
                text_modified,
                character_description,
                text,
                self.db_session_maker,
            )
        )

        # Build button text to display results
        selected_label = f"{selected_provider} 🏆"
        other_label = f"{other_provider}"

        return (
            True,
            gr.update(visible=False),
            gr.update(visible=False),
            (
                gr.update(value=selected_label, visible=True, elem_classes="winner")
                if selected_option == constants.OPTION_A_KEY
                else gr.update(value=other_label, visible=True)
            ),
            (
                gr.update(value=other_label, visible=True)
                if selected_option == constants.OPTION_A_KEY
                else gr.update(value=selected_label, visible=True, elem_classes="winner")
            ),
            gr.update(interactive=True),
        )

    async def randomize_character_description(self) -> Tuple[gr.Dropdown, gr.Textbox]:
        """
        Randomly selects a character description, generates text, and synthesizes speech.

        Returns:
            Tuple containing updates for:
                - sample_character_description_dropdown (select random)
                - character_description_input (update value)
        """
        sample_keys = list(SAMPLE_CHARACTER_DESCRIPTIONS.keys())
        random_sample = random.choice(sample_keys)
        character_description = SAMPLE_CHARACTER_DESCRIPTIONS[random_sample]

        logger.info(f"Randomize All: Selected '{random_sample}'")

        return (
            gr.update(value=random_sample), # Update dropdown
            gr.update(value=character_description), # Update character description
        )

    def disable_ui(self) -> Tuple[
        gr.Button,
        gr.Dropdown,
        gr.Textbox,
        gr.Button,
        gr.Textbox,
        gr.Button,
        gr.Button,
        gr.Button
    ]:
        """
        Disables all interactive components in the UI (except audio players)
        """
        return(
            gr.update(interactive=False), # disable Randomize All button
            gr.update(interactive=False), # disable Character Description dropdown
            gr.update(interactive=False), # disable Character Description input
            gr.update(interactive=False), # disable Generate Text button
            gr.update(interactive=False), # disable Input Text input
            gr.update(interactive=False), # disable Synthesize Speech Button
            gr.update(interactive=False), # disable Select A Button
            gr.update(interactive=False), # disable Select B Button
        )

    def enable_ui(self, should_enable_vote_buttons) -> Tuple[
        gr.Button,
        gr.Dropdown,
        gr.Textbox,
        gr.Button,
        gr.Textbox,
        gr.Button,
        gr.Button,
        gr.Button
    ]:
        """
        Enables all interactive components in the UI (except audio players)
        """
        return(
            gr.update(interactive=True), # enable Randomize All button
            gr.update(interactive=True), # enable Character Description dropdown
            gr.update(interactive=True), # enable Character Description input
            gr.update(interactive=True), # enable Generate Text button
            gr.update(interactive=True), # enable Input Text input
            gr.update(interactive=True), # enable Synthesize Speech Button
            gr.update(interactive=should_enable_vote_buttons), # enable Select A Button
            gr.update(interactive=should_enable_vote_buttons), # enable Select B Button
        )

    def reset_voting_ui(self) -> Tuple[
        gr.Audio,
        gr.Audio,
        gr.Button,
        gr.Button,
        gr.Textbox,
        gr.Textbox,
        OptionMap,
        bool,
        bool,
    ]:
        """
        Resets voting UI state and clear audio players
        """
        default_option_map: OptionMap = {
            "option_a": {"provider": constants.HUME_AI, "generation_id": None, "audio_file_path": ""},
            "option_b": {"provider": constants.HUME_AI, "generation_id": None, "audio_file_path": ""},
        }
        return (
            gr.update(value=None),  # clear audio for audio player A
            gr.update(value=None, autoplay=False), # clear audio and disable autoplay for audio player B
            gr.update(visible=True), # show vote button A
            gr.update(visible=True), # show vote button B
            gr.update(visible=False, elem_classes=[]), # hide vote result A and clear custom styling
            gr.update(visible=False, elem_classes=[]), # hide vote result B and clear custom styling
            default_option_map, # Reset option_map_state as a default OptionMap
            False, # Reset vote_submitted_state
            False, # Reset should_enable_vote_buttons state
        )

    def build_arena_section(self) -> None:
        """
        Builds the Arena section
        """
        # --- UI components ---
        with gr.Row():
            with gr.Column(scale=5):
                gr.HTML(
                    value="""
                    <h2 class="tab-header">📋 Instructions</h2>
                    <ol style="padding-left: 8px;">
                        <li>
                            Select a sample character, or input a custom character description and click
                            <strong>"Generate Text"</strong>, to generate your text input.
                        </li>
                        <li>
                            Click the <strong>"Synthesize Speech"</strong> button to synthesize two TTS outputs based on
                            your text and character description.
                        </li>
                        <li>
                            Listen to both audio samples to compare their expressiveness.
                        </li>
                        <li>
                            Vote for the most expressive result by clicking either <strong>"Select Option A"</strong> or
                            <strong>"Select Option B"</strong>.
                        </li>
                    </ol>
                    """,
                    padding=False,
                )
            randomize_all_button = gr.Button(
                "🎲 Randomize All",
                variant="primary",
                elem_classes="randomize-btn",
                scale=1,
            )

        sample_character_description_dropdown = gr.Dropdown(
            choices=list(SAMPLE_CHARACTER_DESCRIPTIONS.keys()),
            label="Sample Characters",
            info="Generate text with a sample character description.",
            value=None,
            interactive=True,
        )

        with gr.Group():
            character_description_input = gr.Textbox(
                label="Character Description",
                placeholder="Enter a custom character description...",
                lines=2,
                max_lines=8,
                max_length=constants.CHARACTER_DESCRIPTION_MAX_LENGTH,
                show_copy_button=True,
            )
            generate_text_button = gr.Button("Generate Text", variant="secondary")

        with gr.Group():
            text_input = gr.Textbox(
                label="Input Text",
                placeholder="Enter or generate text for synthesis...",
                interactive=True,
                autoscroll=False,
                lines=2,
                max_lines=8,
                max_length=constants.CHARACTER_DESCRIPTION_MAX_LENGTH,
                show_copy_button=True,
            )

        synthesize_speech_button = gr.Button("Synthesize Speech", variant="primary")

        with gr.Row(equal_height=True):
            with gr.Column():
                with gr.Group():
                    option_a_audio_player = gr.Audio(
                        label=OPTION_A_LABEL,
                        type="filepath",
                        interactive=False,
                        show_download_button=False,
                    )
                    vote_button_a = gr.Button(constants.SELECT_OPTION_A, interactive=False)
                    vote_result_a = gr.Textbox(
                        interactive=False,
                        visible=False,
                        elem_id="vote-result-a",
                        text_align="center",
                        container=False,
                    )
            with gr.Column():
                with gr.Group():
                    option_b_audio_player = gr.Audio(
                        label=OPTION_B_LABEL,
                        type="filepath",
                        interactive=False,
                        show_download_button=False,
                    )
                    vote_button_b = gr.Button(constants.SELECT_OPTION_B, interactive=False)
                    vote_result_b = gr.Textbox(
                        interactive=False,
                        visible=False,
                        elem_id="vote-result-b",
                        text_align="center",
                        container=False,
                    )

        # --- UI state components ---
        # Track character description used for text and voice generation
        character_description_state = gr.State("")
        # Track text used for speech synthesis
        text_state = gr.State("")
        # Track generated text state
        generated_text_state = gr.State("")
        # Track whether text that was used was generated or modified/custom
        text_modified_state = gr.State()
        # Track option map (option A and option B are randomized)
        option_map_state = gr.State({})  # OptionMap state as a dictionary
        # Track whether the user has voted for an option
        vote_submitted_state = gr.State(False)
        # Track whether the vote buttons should be enabled
        should_enable_vote_buttons = gr.State(False)

        # --- Register event handlers ---
        # "Randomize All" button click event handler chain
        # 1. Disable interactive UI components
        # 2. Reset UI state for audio players and voting results
        # 3. Select random sample character description
        # 4. Generate text
        # 5. Synthesize speech
        # 6. Enable interactive UI components
        randomize_all_button.click(
            fn=self.disable_ui,
            inputs=[],
            outputs=[
                randomize_all_button,
                sample_character_description_dropdown,
                character_description_input,
                generate_text_button,
                text_input,
                synthesize_speech_button,
                vote_button_a,
                vote_button_b,
            ],
        ).then(
            fn=self.reset_voting_ui,
            inputs=[],
            outputs=[
                option_a_audio_player,
                option_b_audio_player,
                vote_button_a,
                vote_button_b,
                vote_result_a,
                vote_result_b,
                option_map_state,
                vote_submitted_state,
                should_enable_vote_buttons,
            ],
        ).then(
            fn=self.randomize_character_description,
            inputs=[],
            outputs=[sample_character_description_dropdown, character_description_input],
        ).then(
            fn=self.generate_text,
            inputs=[character_description_input],
            outputs=[text_input, generated_text_state],
        ).then(
            fn=self.synthesize_speech,
            inputs=[character_description_input, text_input, generated_text_state],
            outputs=[
                option_a_audio_player,
                option_b_audio_player,
                option_map_state,
                text_modified_state,
                text_state,
                character_description_state,
                should_enable_vote_buttons,
            ],
        ).then(
            fn=self.enable_ui,
            inputs=[should_enable_vote_buttons],
            outputs=[
                randomize_all_button,
                sample_character_description_dropdown,
                character_description_input,
                generate_text_button,
                text_input,
                synthesize_speech_button,
                vote_button_a,
                vote_button_b,
            ],
        )

        # "Sample Characters" dropdown select event handler chain:
        # 1. Update Character Description field with sample
        # 2. Disable interactive UI components
        # 3. Generate text
        # 4. Enable interactive UI components
        sample_character_description_dropdown.select(
            fn=lambda choice: SAMPLE_CHARACTER_DESCRIPTIONS.get(choice, ""),
            inputs=[sample_character_description_dropdown],
            outputs=[character_description_input],
        ).then(
            fn=self.disable_ui,
            inputs=[],
            outputs=[
                randomize_all_button,
                sample_character_description_dropdown,
                character_description_input,
                generate_text_button,
                text_input,
                synthesize_speech_button,
                vote_button_a,
                vote_button_b,
            ],
        ).then(
            fn=self.generate_text,
            inputs=[character_description_input],
            outputs=[text_input, generated_text_state],
        ).then(
            fn=self.enable_ui,
            inputs=[should_enable_vote_buttons],
            outputs=[
                randomize_all_button,
                sample_character_description_dropdown,
                character_description_input,
                generate_text_button,
                text_input,
                synthesize_speech_button,
                vote_button_a,
                vote_button_b,
            ],
        )

        # "Generate Text" button click event handler chain:
        # 1. Disable interactive UI components
        # 2. Generate text
        # 3. Enable interactive UI components
        generate_text_button.click(
            fn=self.disable_ui,
            inputs=[],
            outputs=[
                randomize_all_button,
                sample_character_description_dropdown,
                character_description_input,
                generate_text_button,
                text_input,
                synthesize_speech_button,
                vote_button_a,
                vote_button_b,
            ],
        ).then(
            fn=self.generate_text,
            inputs=[character_description_input],
            outputs=[text_input, generated_text_state],
        ).then(
            fn=self.enable_ui,
            inputs=[should_enable_vote_buttons],
            outputs=[
                randomize_all_button,
                sample_character_description_dropdown,
                character_description_input,
                generate_text_button,
                text_input,
                synthesize_speech_button,
                vote_button_a,
                vote_button_b,
            ],
        )

        # "Text Input" blur event handler
        text_input.blur(
            fn=self.warn_user_about_custom_text,
            inputs=[text_input, generated_text_state],
            outputs=[],
        )

        # "Synthesize Speech" button click event handler chain:
        # 1. Disable components in the UI
        # 2. Reset UI state for audio players and voting results
        # 3. Synthesize speech, load audio players, and display vote button
        # 4. Enable interactive components in the UI
        synthesize_speech_button.click(
            fn=self.disable_ui,
            inputs=[],
            outputs=[
                randomize_all_button,
                sample_character_description_dropdown,
                character_description_input,
                generate_text_button,
                text_input,
                synthesize_speech_button,
                vote_button_a,
                vote_button_b,
            ],
        ).then(
            fn=self.reset_voting_ui,
            inputs=[],
            outputs=[
                option_a_audio_player,
                option_b_audio_player,
                vote_button_a,
                vote_button_b,
                vote_result_a,
                vote_result_b,
                option_map_state,
                vote_submitted_state,
                should_enable_vote_buttons,
            ],
        ).then(
            fn=self.synthesize_speech,
            inputs=[character_description_input, text_input, generated_text_state],
            outputs=[
                option_a_audio_player,
                option_b_audio_player,
                option_map_state,
                text_modified_state,
                text_state,
                character_description_state,
                should_enable_vote_buttons,
            ],
        ).then(
            fn=self.enable_ui,
            inputs=[should_enable_vote_buttons],
            outputs=[
                randomize_all_button,
                sample_character_description_dropdown,
                character_description_input,
                generate_text_button,
                text_input,
                synthesize_speech_button,
                vote_button_a,
                vote_button_b,
            ],
        )

        # "Select Option A"  button click event handler chain:
        vote_button_a.click(
            fn=lambda _=None: (gr.update(interactive=False), gr.update(interactive=False)),
            inputs=[],
            outputs=[vote_button_a, vote_button_b],
        ).then(
            fn=self.submit_vote,
            inputs=[
                vote_submitted_state,
                option_map_state,
                vote_button_a,
                text_modified_state,
                character_description_state,
                text_state,
            ],
            outputs=[
                vote_submitted_state,
                vote_button_a,
                vote_button_b,
                vote_result_a,
                vote_result_b,
                synthesize_speech_button,
            ],
        )

        # "Select Option B"  button click event handler chain:
        vote_button_b.click(
            fn=lambda _=None: (gr.update(interactive=False), gr.update(interactive=False)),
            inputs=[],
            outputs=[vote_button_a, vote_button_b],
        ).then(
            fn=self.submit_vote,
            inputs=[
                vote_submitted_state,
                option_map_state,
                vote_button_b,
                text_modified_state,
                character_description_state,
                text_state,
            ],
            outputs=[
                vote_submitted_state,
                vote_button_a,
                vote_button_b,
                vote_result_a,
                vote_result_b,
                synthesize_speech_button,
            ],
        )

        # Audio Player A stop event handler
        option_a_audio_player.stop(
            # Workaround to play both audio samples back-to-back
            fn=lambda option_map: gr.update(
                value=f"{option_map['option_b']['audio_file_path']}?t={int(time.time())}",
                autoplay=True,
            ),
            inputs=[option_map_state],
            outputs=[option_b_audio_player],
        )

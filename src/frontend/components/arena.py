# Standard Library Imports
import asyncio
import random
import time
from typing import Tuple, Union

# Third-Party Library Imports
import gradio as gr

# Local Application Imports
from src.common import Config, OptionKey, OptionLabel, OptionMap, constants, logger
from src.core import TTSService, VotingService
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
    """
    Handles the user interface logic, state management, and event handling
    for the 'Arena' tab where users generate, synthesize, and compare TTS audio.
    """
    def __init__(self, config: Config, tts_service: TTSService, voting_service: VotingService):
        """
        Initializes the Arena component.

        Args:
            config: The application configuration object.
            tts_service: The service for TTS operations.
            voting_service: The service for voting/leaderboard DB operations.
        """
        self.config: Config = config
        self.tts_service = tts_service
        self.voting_service = voting_service

    def _validate_input_length(
        self,
        input_value: str,
        min_length: int,
        max_length: int,
        input_name: str,
    ) -> None:
        """
        Validates input string length against minimum and maximum limits.

        Args:
            input_value: The string value to validate.
            min_length: The minimum required length (inclusive).
            max_length: The maximum allowed length (inclusive).
            input_name: A descriptive name of the input field (e.g., "character description")
                        used for error messages.

        Raises:
            ValueError: If the input length is outside the specified bounds.
        """
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

    def _validate_character_description_length(self, character_description: str) -> None:
        """
        Validates the character description length using predefined constants.

        Args:
            character_description: The input character description to validate.

        Raises:
            ValueError: If the character description length is invalid.
        """
        self._validate_input_length(
            character_description,
            constants.CHARACTER_DESCRIPTION_MIN_LENGTH,
            constants.CHARACTER_DESCRIPTION_MAX_LENGTH,
            "character description",
        )

    def _validate_text_length(self, text: str) -> None:
        """
        Validates the input text length using predefined constants.

        Args:
            text: The input text to validate.

        Raises:
            ValueError: If the text length is invalid.
        """
        self._validate_input_length(
            text,
            constants.TEXT_MIN_LENGTH,
            constants.TEXT_MAX_LENGTH,
            "text",
        )

    async def _generate_text(self, character_description: str) -> Tuple[dict, str]:
        """
        Validates the character description and generates text using the Anthropic API.

        Args:
            character_description: The user-provided text for character description.

        Returns:
            A tuple containing:
              - A Gradio update dictionary for the text input component.
              - The generated text string (also used for state).

        Raises:
            gr.Error: On validation failure or Anthropic API errors.
        """
        try:
            self._validate_character_description_length(character_description)
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
            logger.error(f"Text Generation Failed: Unexpected error while generating text: {e!s}", exc_info=True)
            raise gr.Error("Failed to generate text. Please try again shortly.")

    def _warn_user_about_custom_text(self, text: str, generated_text: str) -> None:
        """
        Displays a Gradio warning if the input text differs from the generated text state.
        This informs the user that using custom text limits the comparison to only Hume outputs.

        Args:
            text: The current text in the input component.
            generated_text: The original text generated by the system (stored in state).
        """
        if text != generated_text:
            gr.Warning("When custom text is used, only Hume Octave outputs are generated for comparison.")

    async def _synthesize_speech(
        self,
        character_description: str,
        text: str,
        generated_text_state: str,
    ) -> Tuple[dict, dict, OptionMap, bool, str, str, bool]:
        """
        Validates inputs and synthesizes two TTS outputs for comparison.

        Generates TTS audio using different providers (or only Hume if text was
        modified), updates UI state, and returns audio paths and metadata.

        Args:
            character_description: The description used for voice generation.
            text: The text content to synthesize.
            generated_text_state: The previously generated text state to check for modifications.

        Returns:
            A tuple containing:
                - dict: Gradio update for the first audio player (Option A).
                - dict: Gradio update for the second audio player (Option B).
                - OptionMap: Mapping of options ('option_a', 'option_b') to provider details.
                - bool: Flag indicating if the input text was modified from the generated state.
                - str: The text string that was synthesized (for state).
                - str: The character description used (for state).
                - bool: Flag indicating whether the vote buttons should be enabled.

        Raises:
            gr.Error: On validation failure or errors during TTS synthesis API calls.
        """
        try:
            self._validate_character_description_length(character_description)
            self._validate_text_length(text)
        except ValueError as ve:
            logger.error(f"Validation error during speech synthesis: {ve}")
            raise gr.Error(str(ve))

        try:
            text_modified = text != generated_text_state
            options_map: OptionMap = await self.tts_service.synthesize_speech(character_description, text, text_modified)

            # Ensure options_map has the expected keys before accessing
            if "option_a" not in options_map or "option_b" not in options_map:
                 logger.error(f"Invalid options_map received from TTS service: {options_map}")
                 raise gr.Error("Internal error: Failed to retrieve synthesis results correctly.")
            if not options_map.get("option_a") or not options_map.get("option_b"):
                 logger.error(f"Missing data in options_map from TTS service: {options_map}")
                 raise gr.Error("Internal error: Missing synthesis results.")

            return (
                gr.update(value=options_map["option_a"]["audio_file_path"], autoplay=True),
                gr.update(value=options_map["option_b"]["audio_file_path"]),
                options_map,
                text_modified,
                text, # text_state update
                character_description, # character_description_state update
                True, # should_enable_vote_buttons update
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
            logger.error(f"Synthesis failed with an unexpected error during TTS generation: {e!s}", exc_info=True)
            raise gr.Error("An unexpected error occurred. Please try again shortly.")

    def _determine_selected_option(self, selected_option_button_value: str) -> Tuple[OptionKey, OptionKey]:
        """
        Determines the selected option key ('option_a'/'option_b') based on the button value.

        Args:
            selected_option_button_value: The value property of the clicked vote button
                                         (e.g., constants.SELECT_OPTION_A).

        Returns:
            A tuple (selected_option_key, other_option_key).

        Raises:
            ValueError: If the button value is not one of the expected constants.
        """
        if selected_option_button_value == constants.SELECT_OPTION_A:
            selected_option, other_option = constants.OPTION_A_KEY, constants.OPTION_B_KEY
        elif selected_option_button_value == constants.SELECT_OPTION_B:
            selected_option, other_option = constants.OPTION_B_KEY, constants.OPTION_A_KEY
        else:
            logger.error(f"Invalid selected button value received: {selected_option_button_value}")
            raise ValueError(f"Invalid selected button: {selected_option_button_value}")

        return selected_option, other_option

    async def _submit_vote(
        self,
        vote_submitted: bool,
        option_map: OptionMap,
        clicked_option_button_value: str, # Renamed for clarity (it's the button's value, not the component)
        text_modified: bool,
        character_description: str,
        text: str,
    ) -> Tuple[
        Union[bool, gr.skip],
        Union[dict, gr.skip],
        Union[dict, gr.skip],
        Union[dict, gr.skip],
        Union[dict, gr.skip],
        Union[dict, gr.skip]
    ]:
        """
        Handles user voting, submits results asynchronously, and updates the UI.

        Prevents duplicate votes and updates button visibility and result textboxes.

        Args:
            vote_submitted: Boolean state indicating if a vote was already submitted for this pair.
            option_map: The OptionMap dictionary containing details of the two options.
            clicked_option_button_value: The value of the button that was clicked (e.g., constants.SELECT_OPTION_A).
            text_modified: Boolean state indicating if the text was modified by the user.
            character_description: The character description used for synthesis (from state).
            text: The text used for synthesis (from state).

        Returns:
            A tuple of updates for various UI components and state variables,
            or multiple gr.skip() objects if the vote is ignored (e.g., duplicate).
            Elements are:
            - bool | gr.skip: Update for vote_submitted_state (True if vote processed).
            - dict | gr.skip: Update for vote_button_a (visibility).
            - dict | gr.skip: Update for vote_button_b (visibility).
            - dict | gr.skip: Update for vote_result_a (visibility, value, style).
            - dict | gr.skip: Update for vote_result_b (visibility, value, style).
            - dict | gr.skip: Update for synthesize_speech_button (interactivity).
        """
        # If option_map is empty/invalid or vote already submitted, do nothing
        if not isinstance(option_map, dict) or not option_map or vote_submitted:
            logger.warning(f"Vote submission skipped. Option map valid: {isinstance(option_map, dict) and bool(option_map)}, Vote submitted: {vote_submitted}")
            # Return gr.skip() for all outputs
            return gr.skip(), gr.skip(), gr.skip(), gr.skip(), gr.skip(), gr.skip()

        try:
            selected_option, other_option = self._determine_selected_option(clicked_option_button_value)

            # Ensure keys exist before accessing
            if selected_option not in option_map or other_option not in option_map:
                logger.error(f"Selected/Other option key missing in option_map: {selected_option}, {other_option}, Map: {option_map}")
                raise gr.Error("Internal error: Could not process vote due to inconsistent data.")
            if "provider" not in option_map[selected_option] or "provider" not in option_map[other_option]:
                 logger.error(f"Provider missing in option_map entry: Map: {option_map}")
                 raise gr.Error("Internal error: Could not process vote due to missing provider data.")

            selected_provider = option_map[selected_option]["provider"]
            other_provider = option_map[other_option]["provider"]

            # Process vote in the background without blocking the UI
            asyncio.create_task(
                self.voting_service.submit_vote(
                    option_map,
                    selected_option,
                    text_modified,
                    character_description,
                    text,
                )
            )
            logger.info(f"Vote submitted: Selected '{selected_provider}', Other '{other_provider}'")

            # Build result labels
            selected_label = f"{selected_provider} 🏆"
            other_label = f"{other_provider}"

            # Determine which result box gets which label
            result_a_update = gr.update(value=other_label, visible=True)
            result_b_update = gr.update(value=selected_label, visible=True, elem_classes="winner")
            if selected_option == constants.OPTION_A_KEY:
                 result_a_update = gr.update(value=selected_label, visible=True, elem_classes="winner")
                 result_b_update = gr.update(value=other_label, visible=True)


            return (
                True, # Update vote_submitted_state to True
                gr.update(visible=False), # Hide vote button A
                gr.update(visible=False), # Hide vote button B
                result_a_update, # Show/update result textbox A
                result_b_update, # Show/update result textbox B
                gr.update(interactive=True), # Re-enable synthesize speech button
            )
        except ValueError as ve: # Catch error from _determine_selected_option
             logger.error(f"Vote submission failed due to invalid button value: {ve}", exc_info=True)
             # Optionally raise gr.Error or just skip updates
             gr.Error("An internal error occurred while processing your vote.")
             return gr.skip(), gr.skip(), gr.skip(), gr.skip(), gr.skip(), gr.skip()
        except Exception as e:
            logger.error(f"Vote submission failed unexpectedly: {e!s}", exc_info=True)
            gr.Error("An unexpected error occurred while submitting your vote.")
            # Still return skips to avoid partial UI updates
            return gr.skip(), gr.skip(), gr.skip(), gr.skip(), gr.skip(), gr.skip()

    async def _randomize_character_description(self) -> Tuple[dict, dict]:
        """
        Selects a random character description from the predefined samples.

        Returns:
            A tuple containing Gradio update dictionaries for:
                - The sample character dropdown component.
                - The character description input component.
        """
        # Ensure SAMPLE_CHARACTER_DESCRIPTIONS is not empty
        if not SAMPLE_CHARACTER_DESCRIPTIONS:
             logger.warning("SAMPLE_CHARACTER_DESCRIPTIONS is empty. Cannot randomize.")
             # Return updates that clear the fields or do nothing
             return gr.update(value=None), gr.update(value="")

        sample_keys = list(SAMPLE_CHARACTER_DESCRIPTIONS.keys())
        random_sample = random.choice(sample_keys)
        character_description = SAMPLE_CHARACTER_DESCRIPTIONS[random_sample]

        logger.info(f"Randomize All: Selected '{random_sample}'")

        return (
            gr.update(value=random_sample), # Update dropdown selection
            gr.update(value=character_description), # Update character description text
        )

    def _disable_ui(self) -> Tuple[dict, dict, dict, dict, dict, dict, dict, dict]:
        """
        Disables interactive UI components during processing.

        Returns:
            A tuple of Gradio update dictionaries to set interactive=False
            for relevant buttons, dropdowns, and textboxes.
        """
        logger.debug("Disabling UI components.")
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

    def _enable_ui(self, should_enable_vote_buttons: bool) -> Tuple[dict, dict, dict, dict, dict, dict, dict, dict]:
        """
        Enables interactive UI components after processing.

        Args:
            should_enable_vote_buttons: Boolean indicating if the voting buttons
                                         should be enabled (based on synthesis success).

        Returns:
            A tuple of Gradio update dictionaries to set interactive=True
            for relevant buttons, dropdowns, and textboxes. Vote buttons'
            interactivity depends on the input argument.
        """
        logger.debug(f"Enabling UI components. Enable vote buttons: {should_enable_vote_buttons}")
        return(
            gr.update(interactive=True), # enable Randomize All button
            gr.update(interactive=True), # enable Character Description dropdown
            gr.update(interactive=True), # enable Character Description input
            gr.update(interactive=True), # enable Generate Text button
            gr.update(interactive=True), # enable Input Text input
            gr.update(interactive=True), # enable Synthesize Speech Button
            gr.update(interactive=should_enable_vote_buttons), # enable/disable Select A Button
            gr.update(interactive=should_enable_vote_buttons), # enable/disable Select B Button
        )

    def _reset_voting_ui(self) -> Tuple[dict, dict, dict, dict, dict, dict, OptionMap, bool, bool]:
        """
        Resets the voting UI elements to their initial state before new synthesis.

        Clears audio players, makes vote buttons visible, hides result textboxes,
        and resets associated state variables.

        Returns:
            A tuple containing updates for UI components and state variables:
            - dict: Update for audio player A (clear value).
            - dict: Update for audio player B (clear value, disable autoplay).
            - dict: Update for vote button A (make visible).
            - dict: Update for vote button B (make visible).
            - dict: Update for vote result A (hide, clear style).
            - dict: Update for vote result B (hide, clear style).
            - OptionMap: Reset option_map_state to a default placeholder.
            - bool: Reset vote_submitted_state to False.
            - bool: Reset should_enable_vote_buttons state to False.
        """
        logger.debug("Resetting voting UI.")
        default_option_map: OptionMap = {
            "option_a": {"provider": constants.HUME_AI, "generation_id": None, "audio_file_path": ""},
            "option_b": {"provider": constants.HUME_AI, "generation_id": None, "audio_file_path": ""},
        }
        return (
            gr.update(value=None, label=OPTION_A_LABEL),  # clear audio player A, reset label
            gr.update(value=None, autoplay=False, label=OPTION_B_LABEL), # clear audio player B, ensure autoplay off, reset label
            gr.update(visible=True, interactive=False), # show vote button A, ensure non-interactive until enabled
            gr.update(visible=True, interactive=False), # show vote button B, ensure non-interactive until enabled
            gr.update(value="", visible=False, elem_classes=[]), # hide vote result A, clear text/style
            gr.update(value="", visible=False, elem_classes=[]), # hide vote result B, clear text/style
            default_option_map, # Reset option_map_state
            False, # Reset vote_submitted_state
            False, # Reset should_enable_vote_buttons state
        )

    def build_arena_section(self) -> None:
        """
        Constructs the Gradio UI layout for the Arena tab and registers event handlers.

        This method defines all the components within the Arena tab and connects
        button clicks, dropdown selections, etc., to their corresponding handler functions.
        """
        logger.debug("Building Arena UI section...")

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
                    vote_button_a = gr.Button(value=constants.SELECT_OPTION_A, interactive=False)
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
                    vote_button_b = gr.Button(value=constants.SELECT_OPTION_B, interactive=False)
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
        text_modified_state = gr.State(False)
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
            fn=self._disable_ui,
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
            fn=self._reset_voting_ui,
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
            fn=self._randomize_character_description,
            inputs=[],
            outputs=[sample_character_description_dropdown, character_description_input],
        ).then(
            fn=self._generate_text,
            inputs=[character_description_input],
            outputs=[text_input, generated_text_state],
        ).then(
            fn=self._synthesize_speech,
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
            fn=self._enable_ui,
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
            fn=self._disable_ui,
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
            fn=self._generate_text,
            inputs=[character_description_input],
            outputs=[text_input, generated_text_state],
        ).then(
            fn=self._enable_ui,
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
            fn=self._disable_ui,
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
            fn=self._generate_text,
            inputs=[character_description_input],
            outputs=[text_input, generated_text_state],
        ).then(
            fn=self._enable_ui,
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
            fn=self._warn_user_about_custom_text,
            inputs=[text_input, generated_text_state],
            outputs=[],
        )

        # "Synthesize Speech" button click event handler chain:
        # 1. Disable components in the UI
        # 2. Reset UI state for audio players and voting results
        # 3. Synthesize speech, load audio players, and display vote button
        # 4. Enable interactive components in the UI
        synthesize_speech_button.click(
            fn=self._disable_ui,
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
            fn=self._reset_voting_ui,
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
            fn=self._synthesize_speech,
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
            fn=self._enable_ui,
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
            fn=self._submit_vote,
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
            fn=self._submit_vote,
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

        logger.debug("Arena UI section built.")

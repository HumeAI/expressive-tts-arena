"""
app.py

Gradio UI for interacting with the Anthropic API, Hume TTS API, and ElevenLabs TTS API.

Users enter a character description, which is processed using Claude by Anthropic to generate text.
The text is then synthesized into speech using different TTS provider APIs.
Users can compare the outputs and vote for their favorite in an interactive UI.
"""

# Standard Library Imports
import asyncio
import time
from typing import Tuple

# Third-Party Library Imports
import gradio as gr

# Local Application Imports
from src import constants
from src.config import Config, logger
from src.custom_types import Option, OptionMap
from src.database.database import AsyncDBSessionMaker
from src.integrations import (
    AnthropicError,
    ElevenLabsError,
    HumeError,
    generate_text_with_claude,
    text_to_speech_with_elevenlabs,
    text_to_speech_with_hume,
)
from src.utils import (
    create_shuffled_tts_options,
    determine_selected_option,
    get_random_provider,
    submit_voting_results,
    validate_character_description_length,
    validate_text_length,
)


class App:
    config: Config
    db_session_maker: AsyncDBSessionMaker

    def __init__(self, config: Config, db_session_maker: AsyncDBSessionMaker):
        self.config = config
        self.db_session_maker = db_session_maker

    async def _generate_text(
        self,
        character_description: str,
    ) -> Tuple[gr.Textbox, str]:
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
            validate_character_description_length(character_description)
        except ValueError as ve:
            logger.warning(f"Validation error: {ve}")
            raise gr.Error(str(ve))

        try:
            generated_text = await generate_text_with_claude(character_description, self.config)
            logger.info(f"Generated text ({len(generated_text)} characters).")
            return gr.update(value=generated_text), generated_text
        except AnthropicError as ae:
            logger.error(f"AnthropicError while generating text: {ae!s}")
            raise gr.Error(f'There was an issue communicating with the Anthropic API: "{ae.message}"')
        except Exception as e:
            logger.error(f"Unexpected error while generating text: {e}")
            raise gr.Error("Failed to generate text. Please try again later.")

    async def _synthesize_speech(
        self,
        character_description: str,
        text: str,
        generated_text_state: str,
    ) -> Tuple[gr.Audio, gr.Audio, OptionMap, bool, str, str]:
        """
        Synthesizes two text-to-speech outputs, updates UI state components, and returns additional TTS metadata.

        This function generates TTS outputs using different providers based on the input text and its modification
        state. Depending on the selected providers, it may:
          - Synthesize one Hume and one ElevenLabs output (50% chance), or
          - Synthesize two Hume outputs (50% chance).

        The outputs are processed and shuffled, and the corresponding UI components for two audio players are updated.
        Additional metadata such as the comparison type, generation IDs, and state information are also returned.

        Args:
            character_description (str): The description of the character used for generating the voice.
            text (str): The text content to be synthesized into speech.
            generated_text_state (str): The previously generated text state, used to determine if the text has
                                        been modified.

        Returns:
            Tuple containing:
                - dict: Update for the first audio player (with autoplay enabled).
                - dict: Update for the second audio player.
                - OptionMap: A mapping of option constants to their corresponding TTS providers.
                - bool: Flag indicating whether the text was modified.
                - str: The original text that was synthesized.
                - str: The original character description.

        Raises:
            gr.Error: If any API or unexpected errors occur during the TTS synthesis process.
        """
        try:
            validate_character_description_length(character_description)
            validate_text_length(text)
        except ValueError as ve:
            logger.warning(f"Validation error: {ve}")
            raise gr.Error(str(ve))

        text_modified = text != generated_text_state
        provider_a = constants.HUME_AI # always compare with Hume
        provider_b = get_random_provider(text_modified)

        try:
            logger.info(f"Starting speech synthesis with providers: {provider_a} and {provider_b}")
            generation_id_a, audio_a = await text_to_speech_with_hume(character_description, text, self.config)

            tts_provider_funcs = {
                constants.HUME_AI: text_to_speech_with_hume,
                constants.ELEVENLABS: text_to_speech_with_elevenlabs,
            }

            if provider_b not in tts_provider_funcs:
                raise ValueError(f"Unsupported provider: {provider_b}")

            generation_id_b, audio_b = await tts_provider_funcs[provider_b](character_description, text, self.config)

            option_a = Option(provider=provider_a, audio=audio_a, generation_id=generation_id_a)
            option_b = Option(provider=provider_b, audio=audio_b, generation_id=generation_id_b)
            options_map: OptionMap = create_shuffled_tts_options(option_a, option_b)

            return (
                gr.update(value=options_map["option_a"]["audio_file_path"], visible=True, autoplay=True),
                gr.update(value=options_map["option_b"]["audio_file_path"], visible=True),
                options_map,
                text_modified,
                text,
                character_description,
            )
        except ElevenLabsError as ee:
            logger.error(f"ElevenLabsError while synthesizing speech from text: {ee!s}")
            raise gr.Error(f'There was an issue communicating with the Elevenlabs API: "{ee.message}"')

        except HumeError as he:
            logger.error(f"HumeError while synthesizing speech from text: {he!s}")
            raise gr.Error(f'There was an issue communicating with the Hume API: "{he.message}"')

        except Exception as e:
            logger.error(f"Unexpected error during TTS generation: {e}")
            raise gr.Error("An unexpected error occurred. Please try again later.")

    async def _vote(
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
            - A boolean indicating if the vote was accepted.
            - A dict update for hiding vote button A.
            - A dict update for hiding vote button B.
            - A dict update for showing vote result A textbox.
            - A dict update for showing vote result B textbox.
            - A dict update for enabling the synthesize speech button.
        """
        if not option_map or vote_submitted:
            return gr.skip(), gr.skip(), gr.skip(), gr.skip(), gr.skip(), gr.skip()

        selected_option, other_option = determine_selected_option(clicked_option_button)
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
                self.config,
            )
        )

        # Build button text, displaying the provider and voice name, appending the trophy emoji to the selected option.
        selected_label = f"{selected_provider} {constants.TROPHY_EMOJI}"
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

    async def _randomize_character_description(self) -> Tuple[gr.Dropdown, gr.Textbox]:
        """
        Randomly selects a character description, generates text, and synthesizes speech.

        Returns:
            Tuple containing updates for:
            - sample_character_description_dropdown (select random)
            - character_description_input (update value)
        """
        import random

        sample_keys = list(constants.SAMPLE_CHARACTER_DESCRIPTIONS.keys())
        random_sample = random.choice(sample_keys)
        character_description = constants.SAMPLE_CHARACTER_DESCRIPTIONS[random_sample]

        logger.info(f"Randomize All: Selected '{random_sample}'")

        return (
            gr.update(value=random_sample), # Update dropdown
            gr.update(value=character_description), # Update character description
        )

    def _disable_ui(self) -> Tuple[
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
            gr.update(interactive=False), # disable Choose Select A Button
            gr.update(interactive=False), # disable Choose Select B Button
        )

    def _enable_ui(self) -> Tuple[
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
            gr.update(interactive=True), # enable Choose Select A Button
            gr.update(interactive=True), # enable Choose Select B Button
        )

    def _reset_voting_ui(self) -> Tuple[
        gr.Audio,
        gr.Audio,
        gr.Button,
        gr.Button,
        gr.Textbox,
        gr.Textbox,
        OptionMap,
        bool
    ]:
        """
        Resets voting UI state and clear audio players
        """
        default_option_map: OptionMap = {
            "option_a": {"provider": constants.HUME_AI, "generation_id": None, "audio_file_path": ""},
            "option_b": {"provider": constants.HUME_AI, "generation_id": None, "audio_file_path": ""},
        }
        return (
            gr.update(value=None),  # clear audio player A
            gr.update(value=None, autoplay=False),  # clear audio player B
            gr.update(visible=True, interactive=False),  # show vote button A
            gr.update(visible=True, interactive=False),  # show vote button B
            gr.update(visible=False),  # hide vote result A
            gr.update(visible=False),  # hide vote result B
            default_option_map,  # Reset option_map_state as a default OptionMap
            False,  # Reset vote_submitted_state
        )

    def _build_heading_section(self) -> Tuple[gr.HTML, gr.Button, gr.HTML]:
        """
        Builds heading section including title, randomize all button, and instructions
        """
        with gr.Row():
            with gr.Column(scale=5):
                title = gr.HTML("<h1>Expressive TTS Arena</h1>")
            randomize_all_button = gr.Button("🎲 Randomize All", variant="primary", scale=1)
        instructions = gr.HTML(
            """
            <p style="font-size: 16px; font-weight: bold;">
                <strong>Instructions</strong>
            </p>
            <ol style="margin-left: 8px;">
                <li>
                    Choose or enter a character description by selecting a sample or typing your own to guide
                    text generation and voice synthesis.
                </li>
                <li>
                    Click the <strong>"Generate Text"</strong> button to create dialogue for the character;
                    the text automatically populates the input field for further editing.
                </li>
                <li>
                    Click the <strong>"Synthesize Speech"</strong> button to convert your text and character
                    description into two synthesized speech options for direct comparison.
                </li>
                <li>
                    Listen to both audio outputs to assess their expressiveness.
                </li>
                <li>
                    Click <strong>"Select Option A"</strong> or <strong>"Select Option B"</strong> to vote for
                    the most expressive result.
                </li>
            </ol>
            """
        )
        return (title, randomize_all_button, instructions)

    def _build_input_section(self) -> Tuple[gr.Dropdown, gr.Textbox, gr.Button]:
        """
        Builds the input section including the sample character description dropdown, character
        description input, and generate text button.
        """
        sample_character_description_dropdown = gr.Dropdown(
            choices=list(constants.SAMPLE_CHARACTER_DESCRIPTIONS.keys()),
            label="Choose a sample character description",
            value=None,
            interactive=True,
        )
        with gr.Group():
            character_description_input = gr.Textbox(
                label="Character Description",
                placeholder="Enter a character description...",
                lines=3,
                max_lines=8,
                max_length=constants.CHARACTER_DESCRIPTION_MAX_LENGTH,
                show_copy_button=True,
            )
            generate_text_button = gr.Button("Generate Text", variant="secondary")
        return (
            sample_character_description_dropdown,
            character_description_input,
            generate_text_button,
        )

    def _build_output_section(self) -> Tuple[
        gr.Textbox,
        gr.Button,
        gr.Audio,
        gr.Audio,
        gr.Button,
        gr.Button,
        gr.Textbox,
        gr.Textbox,
    ]:
        """
        Builds the output section including text input, audio players, vote buttons, and vote result displays.
        """
        with gr.Group():
            text_input = gr.Textbox(
                label="Input Text",
                placeholder="Enter or generate text for synthesis...",
                interactive=True,
                autoscroll=False,
                lines=3,
                max_lines=8,
                max_length=constants.CHARACTER_DESCRIPTION_MAX_LENGTH,
                show_copy_button=True,
            )
            synthesize_speech_button = gr.Button("Synthesize Speech", variant="primary")

        with gr.Row(equal_height=True):
            with gr.Column():
                with gr.Group():
                    option_a_audio_player = gr.Audio(
                        label=constants.OPTION_A_LABEL,
                        type="filepath",
                        interactive=False,
                    )
                    vote_button_a = gr.Button(
                        constants.SELECT_OPTION_A,
                        interactive=False,
                    )
                    vote_result_a = gr.Textbox(
                        label="",
                        interactive=False,
                        visible=False,
                        elem_id="vote-result-a",
                        text_align="center",
                        container=False,
                    )
            with gr.Column():
                with gr.Group():
                    option_b_audio_player = gr.Audio(
                        label=constants.OPTION_B_LABEL,
                        type="filepath",
                        interactive=False,
                    )
                    vote_button_b = gr.Button(
                        constants.SELECT_OPTION_B,
                        interactive=False,
                    )
                    vote_result_b = gr.Textbox(
                        label="",
                        interactive=False,
                        visible=False,
                        elem_id="vote-result-b",
                        text_align="center",
                        container=False,
                    )

        return (
            text_input,
            synthesize_speech_button,
            option_a_audio_player,
            option_b_audio_player,
            vote_button_a,
            vote_button_b,
            vote_result_a,
            vote_result_b,
        )

    def build_gradio_interface(self) -> gr.Blocks:
        """
        Builds and configures the Gradio user interface.

        Returns:
            gr.Blocks: The fully constructed Gradio UI layout.
        """
        with gr.Blocks(
            title="Expressive TTS Arena",
            fill_width=True,
            css_paths="src/assets/styles.css",
        ) as demo:
            # --- UI components ---
            (
                title,
                randomize_all_button,
                instructions,
            ) = self._build_heading_section()
            (
                sample_character_description_dropdown,
                character_description_input,
                generate_text_button,
            ) = self._build_input_section()
            (
                text_input,
                synthesize_speech_button,
                option_a_audio_player,
                option_b_audio_player,
                vote_button_a,
                vote_button_b,
                vote_result_a,
                vote_result_b,
            ) = self._build_output_section()

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

            # --- Register event handlers ---
            # Select a character description, generate text, and synthesize speech with a single button click.
            # 1. Select random character descriptions and disable buttons
            # 2. Generate text
            # 3. Reset UI state for audio players and voting results
            # 4. Synthesize speech
            # 5. Reenable buttons
            randomize_all_button.click(
                fn=self._randomize_character_description,
                inputs=[],
                outputs=[
                    sample_character_description_dropdown,
                    character_description_input,
                ],
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
                ],
            ).then(
                fn=lambda _=None: gr.update(interactive=False),
                inputs=[],
                outputs=[text_input],
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
                ],
            ).then(
                fn=self._enable_ui,
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
            )

            # When a sample character description is chosen, update the character description textbox
            sample_character_description_dropdown.change(
                fn=lambda choice: constants.SAMPLE_CHARACTER_DESCRIPTIONS.get(choice, ""),
                inputs=[sample_character_description_dropdown],
                outputs=[character_description_input],
            )

            # Generate text button click handler chain:
            # 1. Disable the "Generate text" button
            # 2. Generate text
            # 3. Enable the "Generate text" button
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
            )

            # Synthesize speech button click event handler chain:
            # 1. Disable UI
            # 2. Reset UI state for audio players and voting results
            # 3. Synthesize speech, load audio players, and display vote button
            # 4. Enable the "Synthesize speech" button and display vote buttons
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
                ],
            ).then(
                fn=self._enable_ui,
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
            )

            # Vote button click event handlers
            vote_button_a.click(
                fn=lambda _=None: (
                    gr.update(interactive=False),
                    gr.update(interactive=False),
                ),
                inputs=[],
                outputs=[vote_button_a, vote_button_b],
            ).then(
                fn=self._vote,
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

            vote_button_b.click(
                fn=lambda _=None: (
                    gr.update(interactive=False),
                    gr.update(interactive=False),
                ),
                inputs=[],
                outputs=[vote_button_a, vote_button_b],
            ).then(
                fn=self._vote,
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

            # Reload audio player B with audio and set autoplay to True (workaround to play audio back-to-back)
            option_a_audio_player.stop(
                fn=lambda option_map: gr.update(
                    value=f"{option_map['option_b']['audio_file_path']}?t={int(time.time())}",
                    autoplay=True,
                ),
                inputs=[option_map_state],
                outputs=[option_b_audio_player],
            )

            # Enable voting after second audio option playback finishes
            option_b_audio_player.stop(
                fn=lambda _=None: gr.update(autoplay=False),
                inputs=[],
                outputs=[option_b_audio_player],
            )

        logger.debug("Gradio interface built successfully")
        return demo

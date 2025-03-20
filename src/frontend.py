"""
frontend.py

Gradio UI for interacting with the Anthropic API, Hume TTS API, and ElevenLabs TTS API.

Users enter a character description, which is processed using Claude by Anthropic to generate text.
The text is then synthesized into speech using different TTS provider APIs.
Users can compare the outputs and vote for their favorite in an interactive UI.
"""

# Standard Library Imports
import asyncio
import hashlib
import json
import time
from typing import List, Tuple

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
    get_leaderboard_data,
    get_random_provider,
    submit_voting_results,
    validate_character_description_length,
    validate_text_length,
)


class Frontend:
    config: Config
    db_session_maker: AsyncDBSessionMaker

    def __init__(self, config: Config, db_session_maker: AsyncDBSessionMaker):
        self.config = config
        self.db_session_maker = db_session_maker

        # leaderboard update state
        self._leaderboard_data: List[List[str]] = [[]]
        self._leaderboard_cache_hash = None
        self._last_leaderboard_update_time = 0
        self._min_refresh_interval = 30

    async def _update_leaderboard_data(self, force: bool = False) -> bool:
        """
        Fetches the latest leaderboard data only if needed based on cache and time constraints.
        
        Args:
            force (bool): If True, bypass the time-based throttling.
        
        Returns:
            bool: True if the leaderboard was updated, False otherwise.
        """
        current_time = time.time()
        time_since_last_update = current_time - self._last_leaderboard_update_time
        
        # Skip update if it's been less than min_refresh_interval seconds and not forced
        if not force and time_since_last_update < self._min_refresh_interval:
            logger.debug(f"Skipping leaderboard update: last updated {time_since_last_update:.1f}s ago.")
            return False
            
        # Fetch the latest data
        latest_leaderboard_data = await get_leaderboard_data(self.db_session_maker)
        
        # Generate a hash of the new data to check if it's changed
        data_str = json.dumps(str(latest_leaderboard_data))
        data_hash = hashlib.md5(data_str.encode()).hexdigest()
        
        # Check if the data has changed
        if data_hash == self._leaderboard_cache_hash and not force:
            logger.debug("Leaderboard data unchanged since last fetch.")
            return False
        
        # Update the cache and timestamp
        self._leaderboard_data = latest_leaderboard_data
        self._leaderboard_cache_hash = data_hash
        self._last_leaderboard_update_time = current_time
        logger.info("Leaderboard data updated successfully.")
        return True

    async def _generate_text(self, character_description: str) -> Tuple[gr.Textbox, str]:
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
            logger.error(f"Text Generation Failed: AnthropicError while generating text: {ae!s}")
            raise gr.Error(f'There was an issue communicating with the Anthropic API: "{ae.message}"')
        except Exception as e:
            logger.error(f"Text Generation Failed: Unexpected error while generating text: {e!s}")
            raise gr.Error("Failed to generate text. Please try again shortly.")

    async def _synthesize_speech(
        self,
        character_description: str,
        text: str,
        generated_text_state: str,
    ) -> Tuple[gr.Audio, gr.Audio, OptionMap, bool, str, str, bool]:
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
                - bool: Flag indicating whether the vote buttons should be enabled

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

        tts_provider_funcs = {
            constants.HUME_AI: text_to_speech_with_hume,
            constants.ELEVENLABS: text_to_speech_with_elevenlabs,
        }

        if provider_b not in tts_provider_funcs:
            raise ValueError(f"Unsupported provider: {provider_b}")

        try:
            logger.info(f"Starting speech synthesis with providers: {provider_a} and {provider_b}")

            # Create two tasks for concurrent execution
            task_a = text_to_speech_with_hume(character_description, text, self.config)
            task_b = tts_provider_funcs[provider_b](character_description, text, self.config)

            # Await both tasks concurrently using asyncio.gather()
            (generation_id_a, audio_a), (generation_id_b, audio_b) = await asyncio.gather(task_a, task_b)
            logger.info(f"Synthesis succeeded for providers: {provider_a} and {provider_b}")

            option_a = Option(provider=provider_a, audio=audio_a, generation_id=generation_id_a)
            option_b = Option(provider=provider_b, audio=audio_b, generation_id=generation_id_b)
            options_map: OptionMap = create_shuffled_tts_options(option_a, option_b)

            return (
                gr.update(value=options_map["option_a"]["audio_file_path"], autoplay=True),
                gr.update(value=options_map["option_b"]["audio_file_path"]),
                options_map,
                text_modified,
                text,
                character_description,
                True,
            )
        except ElevenLabsError as ee:
            logger.error(f"Synthesis failed with ElevenLabsError during TTS generation: {ee!s}")
            raise gr.Error(f'There was an issue communicating with the Elevenlabs API: "{ee.message}"')
        except HumeError as he:
            logger.error(f"Synthesis failed with HumeError during TTS generation: {he!s}")
            raise gr.Error(f'There was an issue communicating with the Hume API: "{he.message}"')
        except Exception as e:
            logger.error(f"Synthesis failed with an unexpected error during TTS generation: {e!s}")
            raise gr.Error("An unexpected error occurred. Please try again shortly.")

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

    async def _refresh_leaderboard(self, force: bool = False) -> gr.DataFrame:
        """
        Asynchronously fetches and formats the latest leaderboard data.

        Args:
            force (bool): If True, bypass time-based throttling.

        Returns:
            gr.DataFrame: Updated DataFrame or gr.skip() if no update needed
        """
        data_updated = await self._update_leaderboard_data(force=force)

        if not self._leaderboard_data:
            raise gr.Error("Unable to retrieve leaderboard data. Please refresh the page or try again shortly.")

        # Only return an update if the data changed or force=True
        if data_updated:
            return gr.update(value=self._leaderboard_data)
        else:
            return gr.skip()

    async def _handle_tab_select(self, evt: gr.SelectData):
        """
        Handles tab selection events and refreshes the leaderboard if the Leaderboard tab is selected.
        
        Args:
            evt (gr.SelectData): Event data containing information about the selected tab

        Returns:
            gr.update or gr.skip: Update for the leaderboard table if data changed, otherwise skip
        """
        # Check if the selected tab is "Leaderboard" by name
        if evt.value == "Leaderboard":
            return await self._refresh_leaderboard(force=False)
        return gr.skip()

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
            gr.update(interactive=False), # disable Select A Button
            gr.update(interactive=False), # disable Select B Button
        )

    def _enable_ui(self, should_enable_vote_buttons) -> Tuple[
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

    def _reset_voting_ui(self) -> Tuple[
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

    def _build_title_section(self) -> None:
        """
        Builds the Title section
        """
        gr.HTML(
            """
            <div class="title-container">
                <h1>Expressive TTS Arena</h1>
                <div class="social-links">
                    <a
                        href="https://discord.com/invite/humeai"
                        target="_blank"
                        id="discord-link"
                        title="Join our Discord"
                        aria-label="Join our Discord server"
                    ></a>
                    <a
                        href="https://github.com/HumeAI/expressive-tts-arena"
                        target="_blank"
                        id="github-link"
                        title="View on GitHub"
                        aria-label="View project on GitHub"
                    ></a>
                </div>
            </div>
            <div class="excerpt-container">
                <p>
                    Join the community in evaluating text-to-speech models, and vote for the AI voice that best
                    captures the emotion, nuance, and expressiveness of human speech.
                </p>
            </div>
            """
        )

    def _build_arena_section(self) -> None:
        """
        Builds the Arena section
        """
        # --- UI components ---
        with gr.Row():
            with gr.Column(scale=5):
                gr.HTML(
                    """
                    <h2 class="tab-header">📋 Instructions</h2>
                    <ol>
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
                    """
                )
            randomize_all_button = gr.Button(
                "🎲 Randomize All",
                variant="primary",
                elem_classes="randomize-btn",
                scale=1,
            )

        sample_character_description_dropdown = gr.Dropdown(
            choices=list(constants.SAMPLE_CHARACTER_DESCRIPTIONS.keys()),
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
                        label=constants.OPTION_A_LABEL,
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
                        label=constants.OPTION_B_LABEL,
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
            fn=lambda choice: constants.SAMPLE_CHARACTER_DESCRIPTIONS.get(choice, ""),
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

        # "Select Option B"  button click event handler chain:
        vote_button_b.click(
            fn=lambda _=None: (gr.update(interactive=False), gr.update(interactive=False)),
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

    def _build_leaderboard_section(self) -> gr.DataFrame:
        """
        Builds the Leaderboard section
        """
        # --- UI components ---
        with gr.Row():
            with gr.Column(scale=5):
                gr.HTML(
                    """
                    <h2 class="tab-header">🏆 Leaderboard</h2>
                    <p>
                        This leaderboard presents community voting results for different TTS providers, showing which
                        ones users found more expressive and natural-sounding. The win rate reflects how often each
                        provider was selected as the preferred option in head-to-head comparisons. Click the refresh
                        button to see the most up-to-date voting results.
                    </p>
                    """
                )
            refresh_button = gr.Button(
                "↻ Refresh",
                variant="primary",
                elem_classes="refresh-btn",
                scale=1,
            )

        with gr.Column(elem_id="leaderboard-table-container"):
            leaderboard_table = gr.DataFrame(
                headers=["Rank", "Provider", "Model", "Win Rate", "Votes"],
                datatype=["html", "html", "html", "html", "html"],
                column_widths=[80, 300, 180, 120, 116],
                value=self._leaderboard_data,
                min_width=680,
                interactive=False,
                render=True,
                elem_id="leaderboard-table"
            )

        # Wrapper for the async refresh function
        async def async_refresh_handler():
            return await self._refresh_leaderboard(force=True)
            
        # Handler to re-enable the button after a refresh
        def reenable_button():
            time.sleep(3) # wait 3 seconds before enabling to prevent excessive data fetching
            return gr.update(interactive=True)

        # Refresh button click event handler
        refresh_button.click(
            fn=lambda _=None: (gr.update(interactive=False)),
            inputs=[],
            outputs=[refresh_button],
        ).then(
            fn=async_refresh_handler,
            inputs=[],
            outputs=[leaderboard_table]
        ).then(
            fn=reenable_button,
            inputs=[],
            outputs=[refresh_button]
        )

        return leaderboard_table

    async def build_gradio_interface(self) -> gr.Blocks:
        """
        Builds and configures the fully constructed Gradio UI layout.
        """
        with gr.Blocks(
            title="Expressive TTS Arena",
            css_paths="static/css/styles.css",
        ) as demo:
            await self._update_leaderboard_data()
            self._build_title_section()

            with gr.Tabs() as tabs:
                with gr.TabItem("Arena"):
                    self._build_arena_section()
                with gr.TabItem("Leaderboard"):
                    leaderboard_table = self._build_leaderboard_section()

            tabs.select(
                fn=self._handle_tab_select,
                inputs=[],
                outputs=[leaderboard_table],
            )

        logger.debug("Gradio interface built successfully")
        return demo

"""
app.py

Gradio UI for interacting with the Anthropic API, Hume TTS API, and ElevenLabs TTS API.

Users enter a character description, which is processed using Claude by Anthropic to generate text.
The text is then synthesized into speech using different TTS provider APIs.
Users can compare the outputs and vote for their favorite in an interactive UI.
"""

# Standard Library Imports
import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor
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
from src.theme import CustomTheme
from src.utils import (
    choose_providers,
    create_shuffled_tts_options,
    determine_selected_option,
    submit_voting_results,
    validate_character_description_length,
)


class App:
    config: Config
    db_session_maker: AsyncDBSessionMaker

    def __init__(self, config: Config, db_session_maker: AsyncDBSessionMaker):
        self.config = config
        self.db_session_maker = db_session_maker

    def _generate_text(
        self,
        character_description: str,
    ) -> Tuple[dict, str]:
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
            generated_text = generate_text_with_claude(character_description, self.config)
            logger.info(f"Generated text ({len(generated_text)} characters).")
            return gr.update(value=generated_text), generated_text
        except AnthropicError as ae:
            logger.error(f"AnthropicError while generating text: {ae!s}")
            raise gr.Error(f'There was an issue communicating with the Anthropic API: "{ae.message}"')
        except Exception as e:
            logger.error(f"Unexpected error while generating text: {e}")
            raise gr.Error("Failed to generate text. Please try again later.")

    def _synthesize_speech(
        self,
        character_description: str,
        text: str,
        generated_text_state: str,
    ) -> Tuple[dict, dict, OptionMap, bool, str, str]:
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
        if not text:
            logger.warning("Skipping text-to-speech due to empty text.")
            raise gr.Error("Please generate or enter text to synthesize.")

        # Select 2 TTS providers based on whether the text has been modified.
        text_modified = text != generated_text_state
        provider_a, provider_b = choose_providers(text_modified, character_description)

        try:
            if provider_b == constants.HUME_AI:
                num_generations = 2
                # If generating 2 Hume outputs, do so in a single API call.
                result = text_to_speech_with_hume(character_description, text, num_generations, self.config)
                # Enforce that 4 values are returned.
                if not (isinstance(result, tuple) and len(result) == 4):
                    raise ValueError("Expected 4 values from Hume TTS call when generating 2 outputs")
                generation_id_a, audio_a, generation_id_b, audio_b = result
            else:
                with ThreadPoolExecutor(max_workers=2) as executor:
                    num_generations = 1
                    # Generate a single Hume output.
                    future_audio_a = executor.submit(
                        text_to_speech_with_hume, character_description, text, num_generations, self.config
                    )
                    # Generate a second TTS output from the second provider.
                    match provider_b:
                        case constants.ELEVENLABS:
                            future_audio_b = executor.submit(
                                text_to_speech_with_elevenlabs, character_description, text, self.config
                            )
                        case _:
                            # Additional TTS Providers can be added here.
                            raise ValueError(f"Unsupported provider: {provider_b}")

                    result_a = future_audio_a.result()
                    result_b = future_audio_b.result()
                    if isinstance(result_a, tuple) and len(result_a) >= 2:
                        generation_id_a, audio_a = result_a[0], result_a[1]
                    else:
                        raise ValueError("Unexpected return from text_to_speech_with_hume")
                    if isinstance(result_b, tuple) and len(result_b) >= 2:
                        generation_id_b, audio_b = result_b[0], result_b[1] # type: ignore
                    else:
                        raise ValueError("Unexpected return from text_to_speech_with_elevenlabs")

            # Shuffle options so that placement of options in the UI will always be random.
            option_a = Option(provider=provider_a, audio=audio_a, generation_id=generation_id_a)
            option_b = Option(provider=provider_b, audio=audio_b, generation_id=generation_id_b)
            options_map: OptionMap = create_shuffled_tts_options(option_a, option_b)

            option_a_audio = options_map["option_a"]["audio_file_path"]
            option_b_audio = options_map["option_b"]["audio_file_path"]

            return (
                gr.update(value=option_a_audio, visible=True, autoplay=True),
                gr.update(value=option_b_audio, visible=True),
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


    def _background_submit_vote(
        self,
        option_map: OptionMap,
        selected_option: constants.OptionKey,
        text_modified: bool,
        character_description: str,
        text: str,
    ) -> None:
        """
        Runs the vote submission in a background thread.
        Creates a new event loop and runs the async submit_voting_results function in it.

        Args:
            Same as submit_voting_results

        Returns:
            None
        """
        try:
            # Create a new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # Run the async function in the new loop
            loop.run_until_complete(submit_voting_results(
                option_map,
                selected_option,
                text_modified,
                character_description,
                text,
                self.db_session_maker,
                self.config,
            ))
        except Exception as e:
            logger.error(f"Error in background vote submission thread: {e}", exc_info=True)
        finally:
            # Close the loop when done
            loop.close()


    def _vote(
        self,
        vote_submitted: bool,
        option_map: OptionMap,
        clicked_option_button: str,
        text_modified: bool,
        character_description: str,
        text: str,
    ) -> Tuple[bool, dict, dict, dict]:
        """
        Handles user voting.

        Args:
            vote_submitted (bool): True if a vote was already submitted.
            option_map (OptionMap): A dictionary mapping option labels to their details.
            clicked_option_button (str): The button that was clicked.

        Returns:
            A tuple of:
            - A boolean indicating if the vote was accepted.
            - A dict update for the selected vote button (showing provider and trophy emoji).
            - A dict update for the unselected vote button (showing provider).
            - A dict update for enabling vote interactions.
        """
        if not option_map or vote_submitted:
            return gr.skip(), gr.skip(), gr.skip(), gr.skip()

        selected_option, other_option = determine_selected_option(clicked_option_button)
        selected_provider = option_map[selected_option]["provider"]
        other_provider = option_map[other_option]["provider"]

        # Start a background thread for the database operation
        thread = threading.Thread(
            target=self._background_submit_vote,
            args=(
                option_map,
                selected_option,
                text_modified,
                character_description,
                text,
            ),
            daemon=True
        )
        thread.start()

        # Build button text, displaying the provider and voice name, appending the trophy emoji to the selected option.
        selected_label = f"{selected_provider} {constants.TROPHY_EMOJI}"
        other_label = f"{other_provider}"

        return (
            True,
            (
                gr.update(value=selected_label, variant="primary")
                if selected_option == constants.OPTION_A_KEY
                else gr.update(value=other_label, variant="secondary")
            ),
            (
                gr.update(value=other_label, variant="secondary")
                if selected_option == constants.OPTION_A_KEY
                else gr.update(value=selected_label, variant="primary")
            ),
            gr.update(interactive=True),
        )

    def _reset_ui(self) -> Tuple[dict, dict, dict, dict, OptionMap, bool]:
        """
        Resets UI state before generating new text.

        Returns:
            A tuple of updates for:
             - option_a_audio_player (clear audio)
             - option_b_audio_player (clear audio)
             - vote_button_a (disable and reset button text)
             - vote_button_b (disable and reset button text)
             - option_map_state (reset option map state)
             - vote_submitted_state (reset submitted vote state)
        """
        default_option_map: OptionMap = {
            "option_a": {"provider": constants.HUME_AI, "generation_id": None, "audio_file_path": ""},
            "option_b": {"provider": constants.HUME_AI, "generation_id": None, "audio_file_path": ""},
        }
        return (
            gr.update(value=None),
            gr.update(value=None, autoplay=False),
            gr.update(value=constants.SELECT_OPTION_A, variant="secondary"),
            gr.update(value=constants.SELECT_OPTION_B, variant="secondary"),
            default_option_map,  # Reset option_map_state as a default OptionMap
            False,
        )

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

    def _build_output_section(self) -> Tuple[gr.Textbox, gr.Button, gr.Audio, gr.Audio, gr.Button, gr.Button]:
        """
        Builds the output section including text input, audio players, and vote buttons.
        """
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
            option_a_audio_player = gr.Audio(label=constants.OPTION_A_LABEL, type="filepath", interactive=False)
            option_b_audio_player = gr.Audio(label=constants.OPTION_B_LABEL, type="filepath", interactive=False)
        with gr.Row(equal_height=True):
            vote_button_a = gr.Button(constants.SELECT_OPTION_A, interactive=False)
            vote_button_b = gr.Button(constants.SELECT_OPTION_B, interactive=False)
        return (
            text_input,
            synthesize_speech_button,
            option_a_audio_player,
            option_b_audio_player,
            vote_button_a,
            vote_button_b,
        )

    def build_gradio_interface(self) -> gr.Blocks:
        """
        Builds and configures the Gradio user interface.

        Returns:
            gr.Blocks: The fully constructed Gradio UI layout.
        """
        custom_theme = CustomTheme()
        with gr.Blocks(
            title="Expressive TTS Arena",
            theme=custom_theme,
            fill_width=True,
            css_paths="src/assets/styles.css",
        ) as demo:
            # Title & instructions
            gr.Markdown("# Expressive TTS Arena")
            gr.Markdown(
                """
                1. **Choose or enter a character description**: Select a sample from the list or enter your own to guide
                text and voice generation.
                2. **Generate text**: Click **"Generate Text"** to create dialogue based on the character. The generated
                text will appear in the input field automatically—edit it if needed.
                3. **Synthesize speech**: Click **"Synthesize Speech"** to send your text and character description to
                two TTS APIs. Each API generates a voice and synthesizes speech in that voice.
                4. **Listen & compare**: Play both audio options and assess their expressiveness.
                5. **Vote for the best**: Click **"Select Option A"** or **"Select Option B"** to choose the most
                expressive output.
                """
            )

            # Build generate text section
            (
                sample_character_description_dropdown,
                character_description_input,
                generate_text_button,
            ) = self._build_input_section()

            # Build synthesize speech section
            (
                text_input,
                synthesize_speech_button,
                option_a_audio_player,
                option_b_audio_player,
                vote_button_a,
                vote_button_b,
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
                fn=lambda: gr.update(interactive=False),
                inputs=[],
                outputs=[generate_text_button],
            ).then(
                fn=self._generate_text,
                inputs=[character_description_input],
                outputs=[text_input, generated_text_state],
            ).then(
                fn=lambda: gr.update(interactive=True),
                inputs=[],
                outputs=[generate_text_button],
            )

            # Synthesize speech button click event handler chain:
            # 1. Disable the "Synthesize speech" button
            # 2. Reset UI state
            # 3. Synthesize speech, load audio players, and display vote button
            # 4. Enable the "Synthesize speech" button and display vote buttons
            synthesize_speech_button.click(
                fn=lambda: (
                    gr.update(interactive=False),
                    gr.update(interactive=False),
                    gr.update(interactive=False),
                ),
                inputs=[],
                outputs=[synthesize_speech_button, vote_button_a, vote_button_b],
            ).then(
                fn=self._reset_ui,
                inputs=[],
                outputs=[
                    option_a_audio_player,
                    option_b_audio_player,
                    vote_button_a,
                    vote_button_b,
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
                fn=lambda: (
                    gr.update(interactive=True),
                    gr.update(interactive=True),
                    gr.update(interactive=True),
                ),
                inputs=[],
                outputs=[synthesize_speech_button, vote_button_a, vote_button_b],
            )

            # Vote button click event handlers
            vote_button_a.click(
                fn=lambda: (
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
                    synthesize_speech_button,
                ],
            )

            vote_button_b.click(
                fn=lambda: (
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
                fn=lambda _: gr.update(autoplay=False),
                inputs=[],
                outputs=[option_b_audio_player],
            )

        logger.debug("Gradio interface built successfully")
        return demo

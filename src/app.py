"""
app.py

Gradio UI for interacting with the Anthropic API, Hume TTS API, and ElevenLabs TTS API.

Users enter a prompt, which is processed using Claude by Anthropic to generate text.
The text is then synthesized into speech using both Hume and ElevenLabs text-to-speech (TTS) APIs.
Users can compare the outputs and vote for their favorite in an interactive UI.
"""

# Standard Library Imports
from concurrent.futures import ThreadPoolExecutor
import random
from typing import Union, Tuple

# Third-Party Library Imports
import gradio as gr

# Local Application Imports
from src.config import logger
from src.constants import (
    ELEVENLABS,
    HUME_AI,
    OPTION_A,
    OPTION_B,
    PROMPT_MAX_LENGTH,
    PROMPT_MIN_LENGTH,
    SAMPLE_PROMPTS,
    TROPHY_EMOJI,
    UNKNOWN_PROVIDER,
    VOTE_FOR_OPTION_A,
    VOTE_FOR_OPTION_B,
)
from src.integrations import (
    AnthropicError,
    ElevenLabsError,
    generate_text_with_claude,
    get_random_hume_voice_names,
    HumeError,
    text_to_speech_with_elevenlabs,
    text_to_speech_with_hume,
)
from src.theme import CustomTheme
from src.types import OptionMap
from src.utils import truncate_text, validate_prompt_length


def generate_text(
    prompt: str,
) -> Tuple[Union[str, gr.update], gr.update]:
    """
    Validates the prompt and generates text using Anthropic API.

    Args:
        prompt (str): The user-provided text prompt.

    Returns:
        Tuple containing:
          - The generated text (as a gr.update).
          - An update for the generated text state.

    Raises:
        gr.Error: On validation or API errors.
    """
    try:
        validate_prompt_length(prompt, PROMPT_MAX_LENGTH, PROMPT_MIN_LENGTH)
    except ValueError as ve:
        logger.warning(f"Validation error: {ve}")
        raise gr.Error(str(ve))

    try:
        generated_text = generate_text_with_claude(prompt)
        logger.info(f"Generated text ({len(generated_text)} characters).")
        return gr.update(value=generated_text), generated_text
    except AnthropicError as ae:
        logger.error(f"AnthropicError while generating text: {str(ae)}")
        raise gr.Error(
            "There was an issue communicating with the Anthropic API. Please try again later."
        )
    except Exception as e:
        logger.error(f"Unexpected error while generating text: {e}")
        raise gr.Error("Failed to generate text. Please try again.")


def text_to_speech(
    prompt: str, text: str, generated_text_state: str
) -> Tuple[gr.update, gr.update, dict, Union[str, None]]:
    """
    Synthesizes two text to speech outputs, loads the two audio players with the
    output audio, and updates related UI state components.
        - 50% chance to synthesize one Hume and one Elevenlabs output.
        - 50% chance to synthesize two Hume outputs.

    Args:
        prompt (str): The original prompt.
        text (str): The text to synthesize to speech.

    Returns:
        A tuple of:
         - Update for first audio player (with autoplay)
         - Update for second audio player
         - A dictionary mapping options to providers
         - The raw audio value for option B

    Raises:
        gr.Error: On API or unexpected errors.
    """
    if not text:
        logger.warning("Skipping text-to-speech due to empty text.")
        raise gr.Error("Please generate or enter text to synthesize.")

    # If not using generated text, then only compare Hume to Hume
    compare_hume_with_elevenlabs = (text == generated_text_state) and (
        random.random() < 0.5
    )

    # Pre-select two Hume voices pre-emptively in case we compare Hume to Hume to ensure we do not select the same voice twice.
    hume_voice_a, hume_voice_b = get_random_hume_voice_names()

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            provider_a = HUME_AI
            future_audio_a = executor.submit(
                text_to_speech_with_hume, prompt, text, hume_voice_a
            )

            if compare_hume_with_elevenlabs:
                provider_b = ELEVENLABS
                future_audio_b = executor.submit(text_to_speech_with_elevenlabs, text)
            else:
                provider_b = HUME_AI
                future_audio_b = executor.submit(
                    text_to_speech_with_hume, prompt, text, hume_voice_b
                )

            voice_a, audio_a = future_audio_a.result()
            voice_b, audio_b = future_audio_b.result()

        logger.info(
            f"TTS generated: {provider_a}={len(audio_a)} bytes, {provider_b}={len(audio_b)} bytes"
        )
        options = [
            (audio_a, {"provider": provider_a, "voice": voice_a}),
            (audio_b, {"provider": provider_b, "voice": voice_b}),
        ]
        random.shuffle(options)
        option_a_audio, option_b_audio = options[0][0], options[1][0]
        options_map: OptionMap = {OPTION_A: options[0][1], OPTION_B: options[1][1]}

        return (
            gr.update(value=option_a_audio, visible=True, autoplay=True),
            gr.update(value=option_b_audio, visible=True),
            options_map,
            option_b_audio,
        )
    except ElevenLabsError as ee:
        logger.error(f"ElevenLabsError while synthesizing speech from text: {str(ee)}")
        raise gr.Error(
            "There was an issue communicating with the Elevenlabs API. Please try again later."
        )
    except HumeError as he:
        logger.error(f"HumeError while synthesizing speech from text: {str(he)}")
        raise gr.Error(
            "There was an issue communicating with the Hume API. Please try again later."
        )
    except Exception as e:
        logger.error(f"Unexpected error during TTS generation: {e}")
        raise gr.Error("An unexpected error ocurred. Please try again later.")


def vote(
    vote_submitted: bool, option_map: OptionMap, selected_button: str
) -> Tuple[bool, gr.update, gr.update, gr.update]:
    """
    Handles user voting.

    Args:
        vote_submitted (bool): True if a vote was already submitted.
        option_map (OptionMap): A dictionary mapping option labels to their details.
            Expected structure:
            {
                'Option A': '{"provider": "Hume AI", "voice": "<voice_name>"}',
                'Option B': '{"provider": "ElevenLabs", "voice": "<voice_name>"}'
            }
        selected_button (str): The button that was clicked.

    Returns:
        A tuple of:
         - A boolean indicating if the vote was accepted.
         - An update for the selected vote button (showing provider, voice, and trophy emoji).
         - An update for the unselected vote button (showing provider and voice).
         - An update for enabling vote interactions.
    """
    if not option_map or vote_submitted:
        return gr.skip(), gr.skip(), gr.skip(), gr.skip()

    option_a_selected = selected_button == VOTE_FOR_OPTION_A
    selected_option, other_option = (
        (OPTION_A, OPTION_B) if option_a_selected else (OPTION_B, OPTION_A)
    )

    # Parse selected option details from options map
    selected_details = option_map.get(selected_option, {})
    selected_provider = selected_details.get("provider", UNKNOWN_PROVIDER)
    selected_voice = selected_details.get("voice", "")

    # Parse other option details from options map
    other_details = option_map.get(other_option, {})
    other_provider = other_details.get("provider", UNKNOWN_PROVIDER)
    other_voice = other_details.get("voice", "")

    # Build button labels, displaying the provider and voice name, appending the trophy emoji to the selected option.
    selected_label = f"{selected_provider} | Voice: {selected_voice} {TROPHY_EMOJI}"
    other_label = f"{other_provider} | Voice: {other_voice}"

    return (
        True,
        (
            gr.update(value=selected_label, variant="primary", interactive=False)
            if option_a_selected
            else gr.update(value=other_label, variant="secondary", interactive=False)
        ),
        (
            gr.update(value=other_label, variant="secondary", interactive=False)
            if option_a_selected
            else gr.update(value=selected_label, variant="primary", interactive=False)
        ),
        gr.update(interactive=True),
    )


def reset_ui() -> Tuple[gr.update, gr.update, gr.update, gr.update, None, None, bool]:
    """
    Resets UI state before generating new text.

    Returns:
        A tuple of updates for:
         - option_a_audio_player (clear audio)
         - option_b_audio_player (clear audio)
         - vote_button_a (disable and reset button text)
         - vote_button_a (disable and reset button text)
         - option_map_state (reset option map state)
         - option_b_audio_state (reset option B audio state)
         - vote_submitted_state (reset submitted vote state)
    """
    return (
        gr.update(value=None),
        gr.update(value=None),
        gr.update(value=VOTE_FOR_OPTION_A, variant="secondary"),
        gr.update(value=VOTE_FOR_OPTION_B, variant="secondary"),
        None,
        None,
        False,
    )


def build_input_section() -> Tuple[gr.Markdown, gr.Dropdown, gr.Textbox, gr.Button]:
    """Builds the input section including instructions, sample prompt dropdown, prompt input, and generate button"""
    instructions = gr.Markdown(
        """
        1. **Enter or Generate Text:** Type directly in the Text box, or optionally enter a Prompt, click "Generate text", and edit if needed.
        2. **Synthesize Speech:** Click "Synthesize speech" to generate two audio outputs.
        3. **Listen & Compare:** Playback both options (A & B) to hear the differences.
        4. **Vote for Your Favorite:** Click "Vote for option A" or "Vote for option B" to choose the best one.
    """
    )
    sample_prompt_dropdown = gr.Dropdown(
        choices=list(SAMPLE_PROMPTS.keys()),
        label="Choose a sample prompt (or enter your own)",
        value=None,
        interactive=True,
    )
    prompt_input = gr.Textbox(
        label="Prompt",
        placeholder="Enter your prompt...",
        lines=2,
        max_lines=2,
        max_length=PROMPT_MAX_LENGTH,
        show_copy_button=True,
    )
    generate_text_button = gr.Button("Generate text", variant="secondary")
    return (
        instructions,
        sample_prompt_dropdown,
        prompt_input,
        generate_text_button,
    )


def build_output_section() -> (
    Tuple[gr.Textbox, gr.Button, gr.Audio, gr.Audio, gr.Button, gr.Button]
):
    """Builds the output section including generated text, audio players, and vote buttons."""
    text_input = gr.Textbox(
        label="Text",
        placeholder="Enter text to synthesize speech...",
        interactive=True,
        autoscroll=False,
        lines=4,
        max_lines=12,
        max_length=PROMPT_MAX_LENGTH,
        show_copy_button=True,
    )
    synthesize_speech_button = gr.Button("Synthesize speech", variant="primary")
    with gr.Row(equal_height=True):
        option_a_audio_player = gr.Audio(
            label=OPTION_A, type="filepath", interactive=False
        )
        option_b_audio_player = gr.Audio(
            label=OPTION_B, type="filepath", interactive=False
        )
    with gr.Row(equal_height=True):
        vote_button_a = gr.Button(VOTE_FOR_OPTION_A, interactive=False)
        vote_button_b = gr.Button(VOTE_FOR_OPTION_B, interactive=False)
    return (
        text_input,
        synthesize_speech_button,
        option_a_audio_player,
        option_b_audio_player,
        vote_button_a,
        vote_button_b,
    )


def build_gradio_interface() -> gr.Blocks:
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
        # Title
        gr.Markdown("# Expressive TTS Arena")

        # Build generate text section
        (instructions, sample_prompt_dropdown, prompt_input, generate_text_button) = (
            build_input_section()
        )

        # Build synthesize speech section
        (
            text_input,
            synthesize_speech_button,
            option_a_audio_player,
            option_b_audio_player,
            vote_button_a,
            vote_button_b,
        ) = build_output_section()

        # --- UI state components ---

        # Track generated text state
        generated_text_state = gr.State("")
        # Track generated audio for option B for playing automatically after option 1 audio finishes
        option_b_audio_state = gr.State()
        # Track option map (option A and option B are randomized)
        option_map_state = gr.State()
        # Track whether the user has voted for an option
        vote_submitted_state = gr.State(False)

        # --- Register event handlers ---

        # When a sample prompt is chosen, update the prompt textbox
        sample_prompt_dropdown.change(
            fn=lambda choice: SAMPLE_PROMPTS.get(choice, ""),
            inputs=[sample_prompt_dropdown],
            outputs=[prompt_input],
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
            fn=generate_text,
            inputs=[prompt_input],
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
            fn=lambda: gr.update(interactive=False),
            inputs=[],
            outputs=[synthesize_speech_button],
        ).then(
            fn=reset_ui,
            inputs=[],
            outputs=[
                option_a_audio_player,
                option_b_audio_player,
                vote_button_a,
                vote_button_b,
                option_map_state,
                option_b_audio_state,
                vote_submitted_state,
            ],
        ).then(
            fn=text_to_speech,
            inputs=[prompt_input, text_input, generated_text_state],
            outputs=[
                option_a_audio_player,
                option_b_audio_player,
                option_map_state,
                option_b_audio_state,
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
            fn=vote,
            inputs=[vote_submitted_state, option_map_state, vote_button_a],
            outputs=[
                vote_submitted_state,
                vote_button_a,
                vote_button_b,
                synthesize_speech_button,
            ],
        )
        vote_button_b.click(
            fn=vote,
            inputs=[vote_submitted_state, option_map_state, vote_button_b],
            outputs=[
                vote_submitted_state,
                vote_button_a,
                vote_button_b,
                synthesize_speech_button,
            ],
        )

        # Auto-play second audio after first finishes (Workaround to play audio back-to-back)
        # Audio player A stop event handler chain:
        # 1. Clear the audio player A
        # 2. Load audio player A with audio and set auto play to True
        option_a_audio_player.stop(
            fn=lambda _: gr.update(value=None),
            inputs=[],
            outputs=[option_b_audio_player],
        ).then(
            fn=lambda audio: gr.update(value=audio, autoplay=True),
            inputs=[option_b_audio_state],
            outputs=[option_b_audio_player],
        )

        # Enable voting after second audio option playback finishes
        option_b_audio_player.stop(
            fn=lambda _: (
                gr.update(interactive=True),
                gr.update(interactive=True),
                gr.update(autoplay=False),
            ),
            inputs=[],
            outputs=[vote_button_a, vote_button_b, option_b_audio_player],
        )

    logger.debug("Gradio interface built successfully")
    return demo


if __name__ == "__main__":
    logger.info("Launching TTS Arena Gradio app...")
    demo = build_gradio_interface()
    demo.launch()

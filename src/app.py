"""
app.py

Gradio UI for interacting with the Anthropic API, Hume TTS API, and ElevenLabs TTS API.

Users enter a prompt, which is processed using Claude by Anthropic to generate text.
The text is then converted into speech using both Hume and ElevenLabs TTS APIs.
Users can compare the outputs in an interactive UI.
"""

# Standard Library Imports
from concurrent.futures import ThreadPoolExecutor
from functools import partial
import random
# Third-Party Library Imports
import gradio as gr
# Local Application Imports
from src.config import logger
from src.constants import PROMPT_MAX_LENGTH, PROMPT_MIN_LENGTH, SAMPLE_PROMPTS
from src.integrations import generate_text_with_claude, text_to_speech_with_hume, text_to_speech_with_elevenlabs
from src.utils import truncate_text, validate_prompt_length


def process_prompt(prompt: str):
    """
    Generates text from Claude API and converts it to speech using Hume and ElevenLabs.

    Args:
        prompt (str): User-provided text prompt.

    Returns:
        tuple: Generated text, two audio file paths (Hume & ElevenLabs), and 
               a dictionary mapping audio options to providers.
    """
    logger.info(f'Processing prompt: {truncate_text(prompt, max_length=100)}')

    try:
        # Validate prompt length
        validate_prompt_length(prompt, PROMPT_MAX_LENGTH, PROMPT_MIN_LENGTH)

        # Generate text
        generated_text = generate_text_with_claude(prompt)
        logger.info(f'Generated text ({len(generated_text)} characters).')

        # Generate TTS output in parallel
        with ThreadPoolExecutor(max_workers=2) as executor:
            hume_audio, elevenlabs_audio = executor.map(
                lambda func: func(),
                [partial(text_to_speech_with_hume, prompt, generated_text),
                partial(text_to_speech_with_elevenlabs, generated_text)]
            )

        logger.info(
            f'TTS generated: Hume={len(hume_audio)} bytes, '
            f'ElevenLabs={len(elevenlabs_audio)} bytes'
        )

        # Randomize audio order
        options = [(hume_audio, 'Hume TTS'), (elevenlabs_audio, 'ElevenLabs TTS')]
        random.shuffle(options)

        return (
            generated_text,
            options[0][0],  # Option 1 audio
            options[1][0],  # Option 2 audio
            {'Option 1': options[0][1], 'Option 2': options[1][1]},  # Mapping
        )

    except ValueError as ve:
        logger.warning(f'Validation error: {ve}')
        return str(ve), None, None, {}

    except Exception as e:
        logger.error(f'Unexpected error: {e}')
        return 'An error occurred. Please try again.', None, None, {}


def run_process_prompt(prompt: str):
    """
    Manages UI state while processing a prompt.

    Args:
        prompt (str): User input prompt.

    Yields:
        tuple: UI state updates in three stages:
               1. Disables UI and clears previous outputs.
               2. Displays generated content.
               3. Re-enables UI after processing.
    """
    # Disable UI, clear previous outputs
    yield (
        gr.update(interactive=False),
        gr.update(value=None),
        gr.update(value=None),
        gr.update(value=None),
        gr.update(value=None),
        None,
    )

    # Process the prompt
    generated_text, option1_audio, option2_audio, option_mapping = process_prompt(prompt)

    # Display generated text and audio
    yield (
        gr.update(interactive=True),
        gr.update(value=generated_text),
        gr.update(value=option1_audio, autoplay=True),
        gr.update(value=option2_audio),
        gr.update(value=option_mapping),
        option2_audio,
    )


def build_gradio_interface() -> gr.Blocks:
    """
    Constructs the Gradio user interface.

    Returns:
        gr.Blocks: The Gradio UI layout.
    """
    with gr.Blocks() as demo:
        # Title and instructions
        gr.Markdown('# TTS Arena')
        gr.Markdown(
            'Generate text using **Claude by Anthropic**, then compare text-to-speech outputs '
            'from **Hume TTS API** and **ElevenLabs TTS API**.'
        )

        # Input: Sample prompt selection & textbox
        with gr.Row():
            sample_prompt_dropdown = gr.Dropdown(
                choices=list(SAMPLE_PROMPTS.keys()),
                label='Choose a sample prompt (or enter your own)',
                value=None,
                interactive=True,
            )

        with gr.Row():
            prompt_input = gr.Textbox(
                label='Enter your prompt',
                placeholder='Or type your own...',
                lines=2,
                max_lines=2,
            )

        # Generate Button
        generate_button = gr.Button('Generate')

        # Output: Text & audio
        with gr.Column():
            output_text = gr.Textbox(
                label='Generated Text',
                interactive=False,
                lines=8,
                max_lines=12,
            )

            with gr.Row():
                option1_audio_player = gr.Audio(label='Option 1', type='filepath', interactive=False)
                option2_audio_player = gr.Audio(label='Option 2', type='filepath', interactive=False)

        # UI state components
        option_mapping_state = gr.State()
        option2_audio_state = gr.State()

        # Event handlers
        sample_prompt_dropdown.change(
            fn=lambda choice: SAMPLE_PROMPTS.get(choice, ""),
            inputs=[sample_prompt_dropdown],
            outputs=[prompt_input],
        )

        generate_button.click(
            fn=run_process_prompt,
            inputs=[prompt_input],
            outputs=[
                generate_button,
                output_text,
                option1_audio_player,
                option2_audio_player,
                option_mapping_state,
                option2_audio_state,
            ],
        )

        # Auto-play second audio after first finishes
        option1_audio_player.stop(
            fn=lambda _: gr.update(value=None), # Reset audio so Gradio autoplays it when set
            inputs=[],
            outputs=[option2_audio_player],
        ).then(
            fn=lambda audio: gr.update(value=audio, autoplay=True), # Set audio for playback
            inputs=[option2_audio_state],
            outputs=[option2_audio_player],
        )

    logger.debug('Gradio interface built successfully')
    return demo


if __name__ == '__main__':
    logger.info('Launching TTS Arena Gradio app...')
    demo = build_gradio_interface()
    demo.launch()
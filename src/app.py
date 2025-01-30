"""
app.py

This file defines the Gradio user interface for interacting with the Anthropic API, Hume TTS API, and ElevenLabs TTS API.
Users can input prompts, which are processed to generate text using the Claude model via the Anthropic API.
The generated text is then converted to audio using both Hume and ElevenLabs TTS APIs, allowing playback in the Gradio UI.
"""

# Standard Library Imports
from concurrent.futures import ThreadPoolExecutor
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
    Processes the user input by generating text using Claude API, then converting 
    the generated text to speech using both Hume and ElevenLabs TTS APIs.

    Args:
        prompt (str): The user's input prompt.

    Returns:
        tuple: Generated text, two audio paths (Hume & ElevenLabs), and a mapping 
               of audio options to their respective TTS providers.
    """
    logger.info(f'Processing prompt: {truncate_text(prompt, max_length=100)}')

    try:
        # Validate prompt length
        validate_prompt_length(prompt, PROMPT_MAX_LENGTH, PROMPT_MIN_LENGTH)

        # Generate text
        generated_text = generate_text_with_claude(prompt)
        logger.info(f'Generated text successfully (length={len(generated_text)} characters).')

        # Run TTS generation in parallel
        with ThreadPoolExecutor(max_workers=2) as executor:
            hume_future = executor.submit(text_to_speech_with_hume, prompt, generated_text)
            elevenlabs_future = executor.submit(text_to_speech_with_elevenlabs, generated_text)

            # Retrieve results
            hume_audio = hume_future.result()
            elevenlabs_audio = elevenlabs_future.result()

        logger.info(
            f'TTS audio generated: Hume={len(hume_audio)} bytes, '
            f'ElevenLabs={len(elevenlabs_audio)} bytes'
        )

        # Randomly assign audio options
        audio_options = [
            (hume_audio, 'Hume TTS'),
            (elevenlabs_audio, 'ElevenLabs TTS'),
        ]
        random.shuffle(audio_options)

        option1_audio, option1_provider = audio_options[0]
        option2_audio, option2_provider = audio_options[1]

        return generated_text, option1_audio, option2_audio, {
            'Option 1': option1_provider,
            'Option 2': option2_provider,
        }

    except ValueError as ve:
        logger.warning(f'Validation error: {ve}')
        return str(ve), None, None, {}

    except Exception as e:
        logger.error(f'Unexpected error during processing: {e}')
        return 'An unexpected error occurred. Please try again.', None, None, {}


def run_process_prompt(prompt: str):
    """
    Handles the UI state transitions while processing a prompt.

    Args:
        prompt (str): The user's input prompt.

    Yields:
        tuple: Updates to the UI elements in three stages:
               1. Disabling UI and clearing previous outputs.
               2. Displaying generated content.
               3. Re-enabling UI after generation completes.
    """
    # Stage 1: Disable UI and clear previous outputs
    yield (
        gr.update(interactive=False),                   # Disable Generate Button
        gr.update(value=None),                          # Clear generated text
        gr.update(value=None),                          # Clear Option 1 audio
        gr.update(value=None),                          # Clear Option 2 audio
        gr.update(value=None),                          # Clear option mapping
        None,                                           # Reset Option 2 audio state
    )

    # Process the prompt
    generated_text, option1_audio, option2_audio, option_mapping = process_prompt(prompt)

    # Stage 2: Display generated text and first audio (autoplay)
    yield (
        gr.update(interactive=True),                    # Enable Generate Button
        gr.update(value=generated_text),                # Show generated text
        gr.update(value=option1_audio, autoplay=True),  # Set Option 1 audio
        gr.update(value=option2_audio),                 # Set Option 2 audio
        gr.update(value=option_mapping),                # Store option mapping
        option2_audio,                                  # Store Option 2 audio
    )


def build_gradio_interface() -> gr.Blocks:
    """
    Constructs the Gradio user interface.

    Returns:
        gr.Blocks: The Gradio Blocks-based UI.
    """
    with gr.Blocks() as demo:
        # UI title & instructions
        gr.Markdown('# TTS Arena')
        gr.Markdown(
            'Generate text from a prompt using **Claude by Anthropic**, '
            'and compare text-to-speech outputs from **Hume TTS API** and **ElevenLabs TTS API**.'
        )

        # Prompt selection
        with gr.Row():
            sample_prompt_dropdown = gr.Dropdown(
                choices=list(SAMPLE_PROMPTS.keys()),
                label='Choose a sample prompt (or enter your own below)',
                value=None,
                interactive=True,
            )

        # Prompt input
        with gr.Row():
            prompt_input = gr.Textbox(
                label='Enter your prompt',
                placeholder='Or type your own prompt here...',
                lines=2,
                max_lines=2
            )

        # Generate button
        with gr.Row():
            generate_button = gr.Button('Generate')

        # Output section
        with gr.Column():
            output_text = gr.Textbox(
                label='Generated Text',
                interactive=False,
                lines=8,
                max_lines=12,
            )

            with gr.Row():
                option1_audio_player = gr.Audio(label='Option 1', type='filepath', interactive=False)
                option2_audio_player = gr.Audio(label='Option 2', type='filepath',  interactive=False)

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

        # Auto-play second audio after first completes
        option1_audio_player.stop(
            fn=lambda _: gr.update(value=None),  # Reset first audio before playing second
            inputs=[option1_audio_player],
            outputs=[option2_audio_player],
        ).then(
            fn=lambda option2_audio: gr.update(value=option2_audio, autoplay=True),
            inputs=[option2_audio_state],
            outputs=[option2_audio_player],
        )

    logger.debug('Gradio interface built successfully')
    return demo


if __name__ == '__main__':
    logger.info('Launching TTS Arena Gradio app...')
    demo = build_gradio_interface()
    demo.launch()
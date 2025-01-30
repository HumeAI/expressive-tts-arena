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
from src.constants import (
    OPTION_ONE, 
    OPTION_TWO,
    VOTE_FOR_OPTION_ONE,
    VOTE_FOR_OPTION_TWO,
    PROMPT_MAX_LENGTH, 
    PROMPT_MIN_LENGTH, 
    SAMPLE_PROMPTS
)
from src.integrations import (
    generate_text_with_claude, 
    text_to_speech_with_hume, 
    text_to_speech_with_elevenlabs
)
from src.theme import CustomTheme
from src.utils import truncate_text, validate_prompt_length


def generate_text(prompt: str):
    """
    Generates text from Claude API.

    Args:
        prompt (str): User-provided text prompt.
    """
    logger.info(f'Generating text with prompt: {truncate_text(prompt, max_length=100)}')
    try:
        # Validate prompt length
        validate_prompt_length(prompt, PROMPT_MAX_LENGTH, PROMPT_MIN_LENGTH)


        # Generate text
        generated_text = generate_text_with_claude(prompt)
        logger.info(f'Generated text ({len(generated_text)} characters).')

        return gr.update(value=generated_text)
    
    except ValueError as ve:
        logger.warning(f'Validation error: {ve}')
        return str(ve)

def text_to_speech(prompt: str, generated_text: str):
    try:
        # Generate TTS output in parallel
        with ThreadPoolExecutor(max_workers=2) as executor:
            hume_audio, elevenlabs_audio = executor.map(
                lambda func: func(),
                [partial(text_to_speech_with_hume, prompt, generated_text),
                partial(text_to_speech_with_elevenlabs, generated_text)]
            )

        logger.info(
            f'TTS generated: Hume={len(hume_audio)} bytes, ElevenLabs={len(elevenlabs_audio)} bytes'
        )

        # Randomize audio order
        options = [(hume_audio, 'Hume AI'), (elevenlabs_audio, 'ElevenLabs')]
        random.shuffle(options)

        option_1_audio = options[0][0]
        option_2_audio = options[1][0]

        option_1_provider = options[0][1]
        option_2_provider = options[1][1]

        options_map = { OPTION_ONE: option_1_provider, OPTION_TWO: option_2_provider }

        return (
            gr.update(value=option_1_audio, autoplay=True), # Set option 1 audio
            gr.update(value=option_2_audio), # Option 2 audio
            options_map, # Set option mapping state
            option_2_audio # Set option 2 audio state
        )

    except Exception as e:
        logger.error(f'Unexpected error: {e}')
        return None, None, {}


def vote(option_mapping: dict, selected_button: str):
    """
    Updates both vote buttons to reflect the user's choice.

    Args:
        option_mapping (dict): Maps "Option 1" and "Option 2" to their TTS providers.
        selected_button (str): The label of the button that was clicked.

    Returns:
        tuple[gr.update, gr.update]: Updated properties for both vote buttons.
    """
    if not option_mapping:
        return gr.update(), gr.update()  # No updates if mapping is missing

    # Determine which option was clicked
    is_option_1 = selected_button == VOTE_FOR_OPTION_ONE
    selected_option = OPTION_ONE if is_option_1 else OPTION_TWO
    other_option = OPTION_TWO if is_option_1 else OPTION_ONE

    # Get provider names
    selected_provider = option_mapping.get(selected_option, 'Unknown')
    other_provider = option_mapping.get(other_option, 'Unknown')

    # Return updated button states
    return (
        gr.update(value=f'{selected_provider} ✔', interactive=False, variant='primary') if is_option_1 else gr.update(value=other_provider, interactive=False, variant='secondary'),
        gr.update(value=other_provider, interactive=False, variant='secondary') if is_option_1 else gr.update(value=f'{selected_provider} ✔', interactive=False, variant='primary'),
        gr.update(interactive=True, variant='primary')
    )


def build_gradio_interface() -> gr.Blocks:
    """
    Constructs the Gradio user interface.

    Returns:
        gr.Blocks: The Gradio UI layout.
    """
    custom_theme = CustomTheme()
    with gr.Blocks(title='Expressive TTS Arena', theme=custom_theme) as demo:
        # Title
        gr.Markdown('# Expressive TTS Arena')

        with gr.Column(variant='compact'):
            # Instructions
            gr.Markdown(
                'Generate text using **Claude by Anthropic**, then compare text-to-speech outputs '
                'from **Hume AI** and **ElevenLabs**. Listen to both samples and vote for your favorite!'
            )

            # Sample prompt select
            sample_prompt_dropdown = gr.Dropdown(
                choices=list(SAMPLE_PROMPTS.keys()),
                label='Choose a sample prompt (or enter your own)',
                value=None,
                interactive=True,
            )

            # Prompt input
            prompt_input = gr.Textbox(
                label='Enter your prompt',
                placeholder='Or type your own...',
                lines=2,
                max_lines=2,
                show_copy_button=True,
            )

        # Generate Button
        generate_button = gr.Button('Generate', variant='primary')

        with gr.Column(variant='compact'):
            # Generated text
            generated_text = gr.Textbox(
                label='Generated Text',
                interactive=False,
                autoscroll=False,
                lines=5,
                max_lines=5,
                show_copy_button=True,
            )

            # Audio players 
            with gr.Row():
                option1_audio_player = gr.Audio(label=OPTION_ONE, type='filepath', interactive=False)
                option2_audio_player = gr.Audio(label=OPTION_TWO, type='filepath', interactive=False)

            # Vote buttons
            with gr.Row():
                vote_button_1 = gr.Button(VOTE_FOR_OPTION_ONE, interactive=False)
                vote_button_2 = gr.Button(VOTE_FOR_OPTION_TWO, interactive=False)

        # UI state components
        option_mapping_state = gr.State()
        option2_audio_state = gr.State()
        generated_text_state = gr.State()

        # Event handlers
        sample_prompt_dropdown.change(
            fn=lambda choice: SAMPLE_PROMPTS.get(choice, ''),
            inputs=[sample_prompt_dropdown],
            outputs=[prompt_input],
        )

        generate_button.click(
            fn=lambda _: (
                gr.update(interactive=False), 
                gr.update(interactive=False, value=VOTE_FOR_OPTION_ONE, variant='secondary'),
                gr.update(interactive=False, value=VOTE_FOR_OPTION_TWO, variant='secondary'),
                None,
                None,
            ),
            inputs=[],
            outputs=[generate_button, vote_button_1, vote_button_2, option_mapping_state, option2_audio_state]
        ).then(
            fn=generate_text,
            inputs=[prompt_input],
            outputs=[generated_text]
        ).then(
            fn=text_to_speech,
            inputs=[prompt_input, generated_text],
            outputs=[option1_audio_player, option2_audio_player, option_mapping_state, option2_audio_state]
        ).then(
            fn=lambda _: gr.update(interactive=True, variation='primary'), 
            inputs=[],
            outputs=[generate_button]
        )

        vote_button_1.click(
            fn=vote,
            inputs=[option_mapping_state, vote_button_1],
            outputs=[vote_button_1, vote_button_2, generate_button]
        )

        vote_button_2.click(
            fn=vote,
            inputs=[option_mapping_state, vote_button_2],
            outputs=[vote_button_1, vote_button_2, generate_button]
        )

        # Auto-play second audio after first finishes
        option1_audio_player.stop(
            fn=lambda _: gr.update(value=None),
            inputs=[],
            outputs=[option2_audio_player],
        ).then(
            fn=lambda audio: gr.update(value=audio, autoplay=True),
            inputs=[option2_audio_state],
            outputs=[option2_audio_player],
        )

        # Enable voting after 2nd audio option playback finishes
        option2_audio_player.stop(
            fn=lambda _: (gr.update(interactive=True), gr.update(interactive=True)),  
            inputs=[],
            outputs=[vote_button_1, vote_button_2],
        )

    logger.debug('Gradio interface built successfully')
    return demo


if __name__ == '__main__':
    logger.info('Launching TTS Arena Gradio app...')
    demo = build_gradio_interface()
    demo.launch()
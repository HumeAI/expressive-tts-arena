"""
app.py

Gradio UI for interacting with the Anthropic API, Hume TTS API, and ElevenLabs TTS API.

Users enter a prompt, which is processed using Claude by Anthropic to generate text.
The text is then synthesized into speech using both Hume and ElevenLabs TTS APIs.
Users can compare the outputs in an interactive UI.
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
    OPTION_ONE, 
    OPTION_TWO,
    PROMPT_MAX_LENGTH, 
    PROMPT_MIN_LENGTH, 
    SAMPLE_PROMPTS,
    TROPHY_EMOJI,
    UNKNOWN_PROVIDER,
    VOTE_FOR_OPTION_ONE,
    VOTE_FOR_OPTION_TWO
)
from src.integrations import (
    AnthropicError,
    ElevenLabsError,
    generate_text_with_claude,
    HumeError,
    text_to_speech_with_elevenlabs,
    text_to_speech_with_hume
)
from src.theme import CustomTheme
from src.utils import truncate_text, validate_prompt_length


def generate_text(prompt: str) -> Tuple[Union[str, gr.update], gr.update]:
    """
    Validates the prompt and generates text using Anthropic API.

    Args:
        prompt (str): The user-provided text prompt.

    Returns:
        Tuple containing:
          - The generated text (as a gr.update) if successful,
          - An update for the "Generate" button.
    
    Raises:
        gr.Error: On validation or API errors.
    """
    try:
        validate_prompt_length(prompt, PROMPT_MAX_LENGTH, PROMPT_MIN_LENGTH)
    except ValueError as ve:
        logger.warning(f'Validation error: {ve}')
        raise gr.Error(str(ve))

    try:
        generated_text = generate_text_with_claude(prompt)
        logger.info(f'Generated text ({len(generated_text)} characters).')
        return gr.update(value=generated_text)
    except AnthropicError as ae:
        logger.error(f'AnthropicError while generating text: {str(ae)}')
        raise gr.Error('There was an issue communicating with the Anthropic API. Please try again later.')
    except Exception as e:
        logger.error(f'Unexpected error while generating text: {e}')
        raise gr.Error('Failed to generate text. Please try again.')


def text_to_speech(prompt: str, generated_text: str) -> Tuple[gr.update, gr.update, dict, Union[str, None]]:
    """
    Synthesizes generated text to speech using Hume and ElevenLabs APIs in parallel.

    Args:
        prompt (str): The original prompt.
        generated_text (str): The generated text.

    Returns:
        A tuple of:
         - Update for first audio player (with autoplay)
         - Update for second audio player
         - A dictionary mapping options to providers
         - The raw audio value for option 2 (if needed)
    
    Raises:
        gr.Error: On API or unexpected errors.
    """
    if not generated_text:
        logger.warning('Skipping text-to-speech due to empty text.')
        return gr.skip(), gr.skip(), gr.skip(), gr.skip()

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_hume = executor.submit(text_to_speech_with_hume, prompt, generated_text)
            future_elevenlabs = executor.submit(text_to_speech_with_elevenlabs, generated_text)
            
            hume_audio = future_hume.result()
            elevenlabs_audio = future_elevenlabs.result()

        logger.info(f'TTS generated: Hume={len(hume_audio)} bytes, ElevenLabs={len(elevenlabs_audio)} bytes')
        options = [(hume_audio, 'Hume AI'), (elevenlabs_audio, 'ElevenLabs')]
        random.shuffle(options)
        option_1_audio, option_2_audio = options[0][0], options[1][0]
        options_map = { OPTION_ONE: options[0][1], OPTION_TWO: options[1][1] }

        return (
            gr.update(value=option_1_audio, autoplay=True),
            gr.update(value=option_2_audio),
            options_map,
            option_2_audio,
        )
    except ElevenLabsError as ee:
        logger.error(f'ElevenLabsError while synthesizing speech from text: {str(ee)}')
        raise gr.Error('There was an issue communicating with the Elevenlabs API. Please try again later.')
    except HumeError as he:
        logger.error(f'HumeError while synthesizing speech from text: {str(he)}')
        raise gr.Error('There was an issue communicating with the Hume API. Please try again later.')
    except Exception as e:
        logger.error(f'Unexpected error during TTS generation: {e}')
        raise gr.Error('An unexpected error ocurred. Please try again later.')


def vote(vote_submitted: bool, option_mapping: dict, selected_button: str) -> Tuple[bool, gr.update, gr.update]:
    """
    Handles user voting.

    Args:
        vote_submitted (bool): True if a vote was already submitted
        option_mapping (dict): Maps option labels to provider names
        selected_button (str): The button clicked

    Returns:
        A tuple of:
         - True if the vote was accepted
         - Update for the selected vote button
         - Update for the unselected vote button
         - Update for re-enabling the Generate button
    """
    if not option_mapping or vote_submitted:
        return gr.skip(), gr.skip(), gr.skip()

    is_option_1 = selected_button == VOTE_FOR_OPTION_ONE
    selected_option, other_option = (OPTION_ONE, OPTION_TWO) if is_option_1 else (OPTION_TWO, OPTION_ONE)
    selected_provider = option_mapping.get(selected_option, UNKNOWN_PROVIDER)
    other_provider = option_mapping.get(other_option, UNKNOWN_PROVIDER)

    return (
        True,
        gr.update(value=f'{selected_provider} {TROPHY_EMOJI}', variant='primary') if is_option_1 
            else gr.update(value=other_provider, variant='secondary'),
        gr.update(value=other_provider, variant='secondary') if is_option_1 
            else gr.update(value=f'{selected_provider} {TROPHY_EMOJI}', variant='primary'),
    )

def reset_ui() -> Tuple[gr.update, gr.update, None, None, bool]:
    """
    Resets UI state before generating new text.

    Returns:
        A tuple of updates for:
         - vote_button_1
         - vote_button_2
         - option_mapping_state
         - option2_audio_state
         - vote_submitted_state
    """
    return (
        gr.update(interactive=False, value=VOTE_FOR_OPTION_ONE, variant='secondary'),
        gr.update(interactive=False, value=VOTE_FOR_OPTION_TWO, variant='secondary'),
        None,
        None,
        False,
    )


def build_input_section() -> Tuple[gr.Markdown, gr.Dropdown, gr.Textbox, gr.Button]:
    """Builds the input section including instructions, sample prompt dropdown, prompt input, and generate button"""
    with gr.Column(variant='compact'):
        instructions = gr.Markdown(
            'Generate text with **Claude by Anthropic**, listen to text-to-speech outputs '
            'from **Hume AI** and **ElevenLabs**, and vote for your favorite!'
        )
        sample_prompt_dropdown = gr.Dropdown(
            choices=list(SAMPLE_PROMPTS.keys()),
            label='Choose a sample prompt (or enter your own)',
            value=None,
            interactive=True,
        )
        prompt_input = gr.Textbox(
            label='Prompt',
            placeholder='Enter your prompt...',
            lines=2,
            max_lines=2,
            show_copy_button=True,
        )
    generate_button = gr.Button('Generate', variant='primary')
    return instructions, sample_prompt_dropdown, prompt_input, generate_button


def build_output_section() -> Tuple[gr.Textbox, gr.Audio, gr.Audio, gr.Button, gr.Button]:
    """Builds the output section including generated text, audio players, and vote buttons."""
    with gr.Column(variant='compact'):
        generated_text = gr.Textbox(
            label='Generated text',
            interactive=False,
            autoscroll=False,
            lines=5,
            max_lines=5,
            max_length=PROMPT_MAX_LENGTH,
            show_copy_button=True,
        )
        with gr.Row(equal_height=True):
            option1_audio_player = gr.Audio(label=OPTION_ONE, type='filepath', interactive=False)
            option2_audio_player = gr.Audio(label=OPTION_TWO, type='filepath', interactive=False)
    with gr.Row():
        vote_button_1 = gr.Button(VOTE_FOR_OPTION_ONE, interactive=False)
        vote_button_2 = gr.Button(VOTE_FOR_OPTION_TWO, interactive=False)
    return generated_text, option1_audio_player, option2_audio_player, vote_button_1, vote_button_2


def build_gradio_interface() -> gr.Blocks:
    """
    Builds and configures the Gradio user interface.

    Returns:
        gr.Blocks: The fully constructed Gradio UI layout.
    """
    custom_theme = CustomTheme()
    with gr.Blocks(
        title='Expressive TTS Arena', 
        theme=custom_theme, 
        fill_width=True, 
        css_paths='src/assets/styles.css'
    ) as demo:
        # Title
        gr.Markdown('# Expressive TTS Arena')

        # Build input section
        instructions, sample_prompt_dropdown, prompt_input, generate_button = build_input_section()

        # Build output section
        generated_text, option1_audio_player, option2_audio_player, vote_button_1, vote_button_2 = build_output_section()

        # UI state components
        option_mapping_state = gr.State()       # Track option map (option 1 and option 2 are randomized)
        option2_audio_state = gr.State()        # Track generated audio for option 2 for playing automatically after option 1 audio finishes
        vote_submitted_state = gr.State(False)  # Track whether the user has voted on an option

        # --- Register event handlers ---

        # When a sample prompt is chosen, update the prompt textbox
        sample_prompt_dropdown.change(
            fn=lambda choice: SAMPLE_PROMPTS.get(choice, ''),
            inputs=[sample_prompt_dropdown],
            outputs=[prompt_input],
        )

        # Generate Button Click Handler Chain:
        # 1. Disable the Generate button
        # 2. Reset UI state
        # 3. Generate text
        # 4. Synthesize TTS
        # 5. Re-enable the Generate button
        generate_button.click(
            fn=lambda: gr.update(interactive=False), # Disable the button immediately
            inputs=[],
            outputs=[generate_button]
        ).then(
            fn=reset_ui,
            inputs=[],
            outputs=[vote_button_1, vote_button_2, option_mapping_state, option2_audio_state, vote_submitted_state],
        ).then(
            fn=generate_text,
            inputs=[prompt_input],
            outputs=[generated_text],
        ).then(
            fn=text_to_speech,
            inputs=[prompt_input, generated_text],
            outputs=[option1_audio_player, option2_audio_player, option_mapping_state, option2_audio_state],
        ).then(
            fn=lambda: gr.update(interactive=True), # Re-enable the button
            inputs=[],
            outputs=[generate_button]
        )

        # Vote button click handlers
        vote_button_1.click(
            fn=vote,
            inputs=[vote_submitted_state, option_mapping_state, vote_button_1],
            outputs=[vote_submitted_state, vote_button_1, vote_button_2],
        )
        vote_button_2.click(
            fn=vote,
            inputs=[vote_submitted_state, option_mapping_state, vote_button_2],
            outputs=[vote_submitted_state, vote_button_1, vote_button_2],
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

        # Enable voting after second audio option playback finishes
        option2_audio_player.stop(
            fn=lambda _: (gr.update(interactive=True), gr.update(interactive=True), gr.update(autoplay=False)),
            inputs=[],
            outputs=[vote_button_1, vote_button_2, option2_audio_player],
        )

    logger.debug('Gradio interface built successfully')
    return demo


if __name__ == '__main__':
    logger.info('Launching TTS Arena Gradio app...')
    demo = build_gradio_interface()
    demo.launch()
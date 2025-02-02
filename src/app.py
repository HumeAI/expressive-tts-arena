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
    get_random_elevenlabs_voice_id,
    get_random_hume_voice_names,
    HumeError,
    text_to_speech_with_elevenlabs,
    text_to_speech_with_hume,
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
    Synthesizes two text to speech outputs and loads the two audio players in the UI with the output audio.
        - 50% of the time one Hume tts output and one Elevenlabs output will be synthesized.
        = 50% of the time two Hume tts outputs will be synthesized.

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

    # compare_hume_with_elevenlabs = random.random() < 0.5
    compare_hume_with_elevenlabs = False
    
    elevenlabs_voice = get_random_elevenlabs_voice_id()
    hume_voice_a, hume_voice_b = get_random_hume_voice_names() # We get two Hume voices preemptively in case we compare Hume with Hume

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            provider_a = HUME_AI
            future_audio_a = executor.submit(text_to_speech_with_hume, prompt, generated_text, hume_voice_a)

            if compare_hume_with_elevenlabs:
                provider_b = ELEVENLABS
                future_audio_b = executor.submit(text_to_speech_with_elevenlabs, generated_text, elevenlabs_voice)
            else:
                provider_b = HUME_AI
                future_audio_b = executor.submit(text_to_speech_with_hume, prompt, generated_text, hume_voice_b)
            
            audio_a, audio_b = future_audio_a.result(), future_audio_b.result()

        logger.info(f'TTS generated: {provider_a}={len(audio_a)} bytes, {provider_b}={len(audio_b)} bytes')
        options = [(audio_a, provider_a), (audio_b, provider_b)]
        random.shuffle(options)
        option_a_audio, option_b_audio = options[0][0], options[1][0]
        options_map = { OPTION_A: options[0][1], OPTION_B: options[1][1] }

        return (
            gr.update(value=option_a_audio, autoplay=True),
            gr.update(value=option_b_audio),
            options_map,
            option_b_audio,
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
    """
    if not option_mapping or vote_submitted:
        return gr.skip(), gr.skip(), gr.skip()

    is_option_a = selected_button == VOTE_FOR_OPTION_A
    selected_option, other_option = (OPTION_A, OPTION_B) if is_option_a else (OPTION_B, OPTION_A)
    selected_provider = option_mapping.get(selected_option, UNKNOWN_PROVIDER)
    other_provider = option_mapping.get(other_option, UNKNOWN_PROVIDER)

    return (
        True,
        gr.update(value=f'{selected_provider} {TROPHY_EMOJI}', variant='primary') if is_option_a 
            else gr.update(value=other_provider, variant='secondary'),
        gr.update(value=other_provider, variant='secondary') if is_option_a 
            else gr.update(value=f'{selected_provider} {TROPHY_EMOJI}', variant='primary'),
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
         - option_mapping_state (reset option map state)
         - option2_audio_state (reset option 2 audio state)
         - vote_submitted_state (reset submitted vote state)
    """
    return (
        gr.update(value=None),
        gr.update(value=None),
        gr.update(interactive=False, value=VOTE_FOR_OPTION_A, variant='secondary'),
        gr.update(interactive=False, value=VOTE_FOR_OPTION_B, variant='secondary'),
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
            max_length=PROMPT_MAX_LENGTH,
            show_copy_button=True,
        )
    generate_button = gr.Button('Generate text', variant='primary')
    return instructions, sample_prompt_dropdown, prompt_input, generate_button


def build_output_section() -> Tuple[gr.Textbox, gr.Audio, gr.Audio, gr.Button, gr.Button]:
    """Builds the output section including generated text, audio players, and vote buttons."""
    with gr.Column(variant='compact'):
        generated_text = gr.Textbox(
            label='Text',
            interactive=False,
            autoscroll=False,
            lines=5,
            max_lines=5,
            max_length=PROMPT_MAX_LENGTH,
            show_copy_button=True,
        )
        with gr.Row(equal_height=True):
            option_a_audio_player = gr.Audio(label=OPTION_A, type='filepath', interactive=False)
            option_b_audio_player = gr.Audio(label=OPTION_B, type='filepath', interactive=False)
    with gr.Row():
        vote_button_a = gr.Button(VOTE_FOR_OPTION_A, interactive=False)
        vote_button_b = gr.Button(VOTE_FOR_OPTION_B, interactive=False)
    return generated_text, option_a_audio_player, option_b_audio_player, vote_button_a, vote_button_b


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
        generated_text, option_a_audio_player, option_b_audio_player, vote_button_a, vote_button_b = build_output_section()

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
            outputs=[
                option_a_audio_player,
                option_b_audio_player,
                vote_button_a, 
                vote_button_b, 
                option_mapping_state, 
                option2_audio_state, 
                vote_submitted_state,
            ],
        ).then(
            fn=generate_text,
            inputs=[prompt_input],
            outputs=[generated_text],
        ).then(
            fn=text_to_speech,
            inputs=[prompt_input, generated_text],
            outputs=[
                option_a_audio_player, 
                option_b_audio_player, 
                option_mapping_state, 
                option2_audio_state,
            ],
        ).then(
            fn=lambda: gr.update(interactive=True), # Re-enable the button
            inputs=[],
            outputs=[generate_button]
        )

        # Vote button click handlers
        vote_button_a.click(
            fn=vote,
            inputs=[vote_submitted_state, option_mapping_state, vote_button_a],
            outputs=[vote_submitted_state, vote_button_a, vote_button_b],
        )
        vote_button_b.click(
            fn=vote,
            inputs=[vote_submitted_state, option_mapping_state, vote_button_b],
            outputs=[vote_submitted_state, vote_button_a, vote_button_b],
        )

        # Auto-play second audio after first finishes (workaround for playing audio back-to-back)
        option_a_audio_player.stop(
            fn=lambda _: gr.update(value=None),
            inputs=[],
            outputs=[option_b_audio_player],
        ).then(
            fn=lambda audio: gr.update(value=audio, autoplay=True),
            inputs=[option2_audio_state],
            outputs=[option_b_audio_player],
        )

        # Enable voting after second audio option playback finishes
        option_b_audio_player.stop(
            fn=lambda _: (gr.update(interactive=True), gr.update(interactive=True), gr.update(autoplay=False)),
            inputs=[],
            outputs=[vote_button_a, vote_button_b, option_b_audio_player],
        )

    logger.debug('Gradio interface built successfully')
    return demo


if __name__ == '__main__':
    logger.info('Launching TTS Arena Gradio app...')
    demo = build_gradio_interface()
    demo.launch()
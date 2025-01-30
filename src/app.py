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
from typing import Union
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
    generate_text_with_claude, 
    text_to_speech_with_hume, 
    text_to_speech_with_elevenlabs
)
from src.theme import CustomTheme
from src.utils import truncate_text, validate_prompt_length


def validate_and_generate_text(prompt: str) -> tuple[Union[str, gr.update], gr.update]:
    """
    Validates the prompt before generating text.
    - If valid, returns the generated text and keeps the button disabled.
    - If invalid, returns an error message and re-enables the button.

    Args:
        prompt (str): The user-provided text prompt.

    Returns:
        tuple[Union[str, gr.update], gr.update]:
            - The generated text or an error message.
            - The updated state of the "Generate" button.
    """
    try:
        validate_prompt_length(prompt, PROMPT_MAX_LENGTH, PROMPT_MIN_LENGTH)  # Raises error if invalid
    except ValueError as ve:
        logger.warning(f'Validation error: {ve}')
        return str(ve), gr.update(interactive=True)  # Show error, re-enable button

    try:
        generated_text = generate_text_with_claude(prompt)
        if not generated_text:
            raise ValueError("Claude API returned an empty response.")

        logger.info(f'Generated text ({len(generated_text)} characters).')
        return gr.update(value=generated_text), gr.update(interactive=False)  # Keep button disabled

    except Exception as e:
        logger.error(f'Error while generating text with Claude API: {e}')
        return "Error: Failed to generate text. Please try again.", gr.update(interactive=True)  # Re-enable button



def text_to_speech(prompt: str, generated_text: str) -> tuple[gr.update, gr.update, dict, str | None]:
    """
    Converts generated text to speech using Hume AI and ElevenLabs APIs.
    
    If the generated text is invalid (empty or an error message), this function
    does nothing and returns `None` values to prevent TTS from running.

    Args:
        prompt (str): The original user-provided prompt.
        generated_text (str): The generated text that will be converted to speech.

    Returns:
        tuple[gr.update, gr.update, dict, Union[str, None]]:
            - `gr.update(value=option_1_audio, autoplay=True)`: Updates the first audio player.
            - `gr.update(value=option_2_audio)`: Updates the second audio player.
            - `options_map`: A dictionary mapping OPTION_ONE and OPTION_TWO to their providers.
            - `option_2_audio`: The second audio file path or `None` if an error occurs.
    """
    if not generated_text or generated_text.startswith("Error:"):
        logger.warning("Skipping TTS generation due to invalid text.")
        return gr.update(value=None), gr.update(value=None), {}, None  # Return empty updates

    try:
        # Generate TTS output in parallel
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_hume = executor.submit(text_to_speech_with_hume, prompt, generated_text)
            future_elevenlabs = executor.submit(text_to_speech_with_elevenlabs, generated_text)
            
            hume_audio = future_hume.result()
            elevenlabs_audio = future_elevenlabs.result()

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
        logger.error(f'Unexpected error during TTS generation: {e}')
        return gr.update(), gr.update(), {}, None


def vote(
    vote_submitted: bool, 
    option_mapping: dict, 
    selected_button: str
) -> tuple[bool, gr.update, gr.update, gr.update]:
    """
    Handles user voting and updates the UI to reflect the selected choice.

    Args:
        vote_submitted (bool): Indicates if a vote has already been submitted.
        option_mapping (dict): Maps "Option 1" and "Option 2" to their respective TTS providers.
        selected_button (str): The button that was clicked by the user.

    Returns:
        tuple[bool, gr.update, gr.update, gr.update]:
            - `True`: Indicates the vote has been submitted.
            - `gr.update`: Updates the selected vote button.
            - `gr.update`: Updates the unselected vote button.
            - `gr.update(interactive=True)`: Enables the "Generate" button after voting.
    """
    if not option_mapping or vote_submitted:
        return True, gr.update(), gr.update(), gr.update()  # No updates if mapping is missing

    # Determine selected option
    is_option_1 = selected_button == VOTE_FOR_OPTION_ONE
    selected_option, other_option = (OPTION_ONE, OPTION_TWO) if is_option_1 else (OPTION_TWO, OPTION_ONE)

    # Get provider names
    selected_provider = option_mapping.get(selected_option, UNKNOWN_PROVIDER)
    other_provider = option_mapping.get(other_option, UNKNOWN_PROVIDER)

    # Return updated button states
    return (
        True,
        gr.update(value=f'{selected_provider} {TROPHY_EMOJI}', variant='primary') if is_option_1 else gr.update(value=other_provider, variant='secondary'),
        gr.update(value=other_provider, variant='secondary') if is_option_1 else gr.update(value=f'{selected_provider} {TROPHY_EMOJI}', variant='primary'),
        gr.update(interactive=True, variant='primary')
    )


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
        css='footer{display:none !important}'
    ) as demo:
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
                show_label=False,
                placeholder='Enter your prompt...',
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
                lines=6,
                max_lines=6,
                max_length=PROMPT_MAX_LENGTH,
                show_copy_button=True,
            )

            # Audio players 
            with gr.Row():
                option1_audio_player = gr.Audio(
                    label=OPTION_ONE, 
                    type='filepath', 
                    interactive=False
                )
                option2_audio_player = gr.Audio(
                    label=OPTION_TWO, 
                    type='filepath', 
                    interactive=False
                )

            # Vote buttons
            with gr.Row():
                vote_button_1 = gr.Button(VOTE_FOR_OPTION_ONE, interactive=False)
                vote_button_2 = gr.Button(VOTE_FOR_OPTION_TWO, interactive=False)

        # UI state components
        option_mapping_state = gr.State() # Track option map (option 1 and option 2 are randomized)
        option2_audio_state = gr.State() # Track generated audio for option 2 for playing automatically after option 1 audio finishes
        generated_text_state = gr.State() # Track the text which was generated from the user's prompt
        vote_submitted_state = gr.State(False) # Track whether the user has voted on an option

        # Event handlers
        sample_prompt_dropdown.change(
            fn=lambda choice: SAMPLE_PROMPTS.get(choice, ''),
            inputs=[sample_prompt_dropdown],
            outputs=[prompt_input],
        )

        generate_button.click(
            # Reset UI
            fn=lambda _: (
                gr.update(interactive=False), 
                gr.update(interactive=False, value=VOTE_FOR_OPTION_ONE, variant='secondary'),
                gr.update(interactive=False, value=VOTE_FOR_OPTION_TWO, variant='secondary'),
                None,
                None,
                False
            ),
            inputs=[],
            outputs=[
                generate_button, 
                vote_button_1, 
                vote_button_2, 
                option_mapping_state, 
                option2_audio_state, 
                vote_submitted_state
            ]
        ).then(
            # Validate and prompt and generate text
            fn=validate_and_generate_text,
            inputs=[prompt_input],
            outputs=[generated_text, generate_button]  # Ensure button gets re-enabled on failure
        ).then(
            # Validate generated text and synthesize text-to-speech
            fn=text_to_speech,
            inputs=[prompt_input, generated_text],  # Pass prompt & generated text
            outputs=[
                option1_audio_player, 
                option2_audio_player, 
                option_mapping_state, 
                option2_audio_state
            ]
        )

        vote_button_1.click(
            fn=vote,
            inputs=[
                vote_submitted_state, 
                option_mapping_state, 
                vote_button_1
            ],
            outputs=[
                vote_submitted_state, 
                vote_button_1, 
                vote_button_2, 
                generate_button
            ]
        )

        vote_button_2.click(
            fn=vote,
            inputs=[
                vote_submitted_state, 
                option_mapping_state, 
                vote_button_2
            ],
            outputs=[
                vote_submitted_state, 
                vote_button_1, 
                vote_button_2, 
                generate_button
            ]
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
            fn=lambda _: (
                gr.update(interactive=True), 
                gr.update(interactive=True),
                gr.update(autoplay=False),
            ),  
            inputs=[],
            outputs=[
                vote_button_1, 
                vote_button_2, 
                option2_audio_player,
            ],
        )

    logger.debug('Gradio interface built successfully')
    return demo


if __name__ == '__main__':
    logger.info('Launching TTS Arena Gradio app...')
    demo = build_gradio_interface()
    demo.launch()
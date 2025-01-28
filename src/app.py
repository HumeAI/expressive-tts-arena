"""
app.py

This file defines the Gradio user interface for interacting with the Anthropic API, Hume TTS API, and ElevenLabs TTS API.
Users can input prompts, which are processed to generate text using the Claude model via the Anthropic API.
The generated text is then converted to audio using both Hume and ElevenLabs TTS APIs, allowing playback in the Gradio UI.

Key Features:
- Gradio interface for user interaction.
- Input validation via prompt length constraints.
- Integration with the Anthropic, Hume, and ElevenLabs APIs.
- Playback support for TTS audio responses.

Functions:
- process_prompt: Handles user input, calls the Anthropic and Hume APIs, and returns generated text and audio.
- build_gradio_interface: Constructs the Gradio Blocks-based interface.
"""

# Third-Party Library Imports
import gradio as gr
# Local Application Imports
from src.config import logger
from src.integrations import generate_text_with_claude, text_to_speech_with_hume, text_to_speech_with_elevenlabs
from src.sample_prompts import SAMPLE_PROMPTS
from src.utils import truncate_text, validate_prompt_length


# Constants
PROMPT_MIN_LENGTH: int = 10
PROMPT_MAX_LENGTH: int = 300


def process_prompt(prompt: str) -> str:
    """
    Process the user prompt and generate text using the Claude API.
    Then convert the generated text to speech using both Hume and ElevenLabs TTS APIs.

    Args:
        prompt (str): The user's input prompt.

    Returns:
        tuple: The generated text and audio data from both Hume and ElevenLabs.
    """
    logger.debug(f"Entering process_prompt with prompt: {prompt}")
    try:
        # Validate prompt length before processing
        validate_prompt_length(prompt, PROMPT_MAX_LENGTH, PROMPT_MIN_LENGTH)

        # Generate text with Claude API
        generated_text = generate_text_with_claude(prompt)
        logger.debug(f"Generated text: {generated_text}")

        # Convert text to speech with Hume TTS API
        hume_audio = text_to_speech_with_hume(prompt, generated_text)
        logger.debug(f"Hume audio data: {len(hume_audio)} bytes")

        # Convert text to speech with ElevenLabs TTS API
        elevenlabs_audio = text_to_speech_with_elevenlabs(generated_text)
        logger.debug(f"ElevenLabs audio data: {len(elevenlabs_audio)} bytes")

        logger.info("Successfully processed prompt.")
        return generated_text, hume_audio, elevenlabs_audio

    except ValueError as ve:
        logger.warning(f"Validation error: {ve}")
        return str(ve), None, None  # Return validation error directly to the UI
    except Exception as e:
        logger.error(f"Unexpected error during processing: {e}")
        return "An unexpected error occurred. Please try again.", None, None


def build_gradio_interface() -> gr.Blocks:
    """
    Build the Gradio user interface.

    Returns:
        gr.Blocks: The Gradio Blocks object representing the interface.
    """
    with gr.Blocks() as demo:
        gr.Markdown("# TTS Arena")
        gr.Markdown(
            "Generate text from a prompt using **Claude by Anthropic**, "
            "and listen to the generated text-to-speech using **Hume TTS API** "
            "and **ElevenLabs TTS API** for comparison."
        )

        with gr.Row():
            # Dropdown for predefined prompts
            sample_prompt_dropdown = gr.Dropdown(
                choices=list(SAMPLE_PROMPTS.keys()),
                label="Choose a Sample Prompt (or enter your own below)",
                interactive=True
            )

        with gr.Row():
            # Custom prompt input
            prompt_input = gr.Textbox(
                label="Enter your custom prompt",
                placeholder="Or type your own custom prompt here...",
                lines=2,
            )

        with gr.Row():
            generate_button = gr.Button("Generate")

        # Display the generated text and audio side by side
        with gr.Row():
            output_text = gr.Textbox(
                label="Generated Text",
                interactive=False,
                lines=16,
                max_lines=24,
                scale=2,
            )
            with gr.Column(scale=1):
                hume_audio_output = gr.Audio(label="Hume TTS Audio", type="filepath")
                elevenlabs_audio_output = gr.Audio(label="ElevenLabs TTS Audio", type="filepath")

        # Auto-fill the text input when a sample is selected
        sample_prompt_dropdown.change(
            fn=lambda choice: SAMPLE_PROMPTS[choice] if choice else "",
            inputs=[sample_prompt_dropdown],
            outputs=[prompt_input],
        )

        # Attach the validation, text generation, and TTS processing logic
        generate_button.click(
            fn=process_prompt,
            inputs=prompt_input,
            outputs=[output_text, hume_audio_output, elevenlabs_audio_output],
        )

    logger.debug("Gradio interface built successfully")
    return demo


if __name__ == "__main__":
    logger.info("Launching TTS Arena Gradio app...")
    demo = build_gradio_interface()
    demo.launch()
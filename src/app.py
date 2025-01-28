"""
app.py

This file defines the Gradio user interface for interacting with the Anthropic API and Hume TTS API.
Users can input prompts, which are processed to generate text using the Claude model via the Anthropic API.
The generated text is then converted to audio using the Hume TTS API, allowing playback in the Gradio UI.

Key Features:
- Gradio interface for user interaction.
- Input validation via prompt length constraints.
- Integration with the Anthropic and Hume APIs.
- Playback support for TTS audio responses.

Functions:
- process_prompt: Handles user input, calls the Anthropic and Hume APIs, and returns generated text and audio.
- build_gradio_interface: Constructs the Gradio Blocks-based interface.
"""

# Third-Party Library Imports
import gradio as gr
# Local Application Imports
from src.integrations import generate_text_with_claude, text_to_speech_with_hume
from src.config import logger
from src.utils import truncate_text, validate_prompt_length


# Constants
PROMPT_MIN_LENGTH: int = 10
PROMPT_MAX_LENGTH: int = 500


def process_prompt(prompt: str) -> str:
    """
    Process the user prompt and generate text using the Claude API.

    Args:
        prompt (str): The user's input prompt.

    Returns:
        str: The generated text or an error message.
    """
    logger.debug(f"Entering process_prompt with prompt: {prompt}")
    try:
        # Validate prompt length before processing
        validate_prompt_length(prompt, PROMPT_MAX_LENGTH, PROMPT_MIN_LENGTH)

        # Generate text with Claude API
        generated_text = generate_text_with_claude(prompt)
        logger.debug(f"Generated text: {generated_text}")

        # Convert text to speech with Hume TTS API
        generated_hume_audio = text_to_speech_with_hume(prompt, generated_text)
        logger.debug(f"Generated audio data: {len(generated_hume_audio)} bytes")

        logger.info("Successfully processed prompt.")
        return generated_text, generated_hume_audio

    except ValueError as ve:
        logger.warning(f"Validation error: {ve}")
        return str(ve), b""  # Return validation error directly to the UI with no audio
    except Exception as e:
        logger.error(f"Unexpected error during processing: {e}")
        return "An unexpected error occurred. Please try again.", b""


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
            "and listen to the generated text-to-speech using **Hume TTS API**."
        )

        with gr.Row():
            prompt_input = gr.Textbox(
                label="Enter your prompt",
                placeholder="Prompt Claude to generate a poem or short story...",
                lines=2,
            )

        with gr.Row():
            generate_button = gr.Button("Generate")

        with gr.Row():
            output_text = gr.Textbox(
                label="Generated Text",
                interactive=False,
                lines=10,
            )
            audio_output = gr.Audio(label="Generated Audio", type="filepath")  # Fix: type="filepath"

        # Attach the validation, text generation, and TTS processing logic
        generate_button.click(
            fn=process_prompt,
            inputs=prompt_input,
            outputs=[output_text, audio_output],
        )

    logger.debug("Gradio interface built successfully")
    return demo


if __name__ == "__main__":
    logger.info("Launching TTS Arena Gradio app...")
    demo = build_gradio_interface()
    demo.launch()
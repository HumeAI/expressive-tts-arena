"""
app.py

This file defines the Gradio user interface for interacting with the Anthropic API.
Users can input prompts, which are processed and passed to the Claude model via the API.
The generated responses are displayed back to the user in the Gradio UI.

Key Features:
- Gradio interface for user interaction.
- Input validation via prompt length constraints.
- Logging of user interactions and API responses.

Functions:
- process_prompt: Handles user input, calls the API, and returns generated text.
- build_gradio_interface: Constructs the Gradio Blocks-based interface.
"""

# Third-Party Library Imports
import gradio as gr
# Local Application Imports
from anthropic_api import generate_text_with_claude
from config import logger
from utils import truncate_text, validate_prompt_length


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
        generated_text = generate_text_with_claude(prompt)
        logger.debug(f"Generated text: {generated_text}")
        logger.info("Successfully generated text.")
        return generated_text
    except ValueError as ve:
        logger.warning(f"Validation error: {ve}")
        return str(ve)  # Return validation error directly to the UI
    except Exception as e:
        logger.error(f"Unexpected error generating text: {e}")
        return "An unexpected error occurred. Please try again."


def build_gradio_interface() -> gr.Blocks:
    """
    Build the Gradio user interface.

    Returns:
        gr.Blocks: The Gradio Blocks object representing the interface.
    """
    with gr.Blocks() as demo:
        gr.Markdown("# TTS Arena")
        gr.Markdown("Generate text from a prompt using **Claude by Anthropic**.")

        with gr.Row():
            prompt_input = gr.Textbox(
                label="Enter your prompt",
                placeholder=f"Prompt Claude to generate a poem or short story...",
                lines=2,
            )

        with gr.Row():
            generate_button = gr.Button("Generate")

        with gr.Row():
            output_text = gr.Textbox(label="Generated Text", interactive=False, lines=10)

        # Attach the validation and processing logic
        generate_button.click(
            fn=process_prompt,
            inputs=prompt_input,
            outputs=output_text,
        )

    logger.debug("Gradio interface built successfully")
    return demo


if __name__ == "__main__":
    logger.info("Launching TTS Arena Gradio app...")
    demo = build_gradio_interface()
    demo.launch()
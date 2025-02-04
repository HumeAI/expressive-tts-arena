<div align="center">   
    <img src="https://storage.googleapis.com/hume-public-logos/hume/hume-banner.png">   
    <h1>Hume AI | Expressive TTS Arena</h1>   
    <p>
        <strong>An interactive platform for comparing and evaluating the expressiveness of different text-to-speech engines</strong>   
    </p> 
</div>

## Overview
Expressive TTS Arena is an open-source web application that enables users to compare text-to-speech outputs with a focus on expressiveness rather than just audio quality. Built with [Gradio](https://www.gradio.app/), it provides a seamless interface for generating and comparing speech synthesis from different providers, including Hume AI and ElevenLabs.

## Features
- Text generation using Claude AI for creating expressive content.
- Direct text input or AI-assisted text generation.
- Comparative analysis of different TTS engines.
- Simple voting mechanism for preferred outputs.
- Random voice selection from multiple providers.
- Real-time speech synthesis comparison.

## Prerequisites

- Python >=3.11.11
- Virtual environment capability
- API keys for Hume AI, Anthropic, and ElevenLabs
- For a complete list of dependencies, see requirements.

### Installation

1. Create and activate the virtual environment:

    ```sh
    python -m venv gradio-env
    source gradio-env/bin/activate  # On Windows, use: gradio-env\Scripts\activate
    ```

2. Install dependencies:

    ```sh
    pip install -r requirements.txt
    ```

3. Configure environment variables:
    - Create a `.env` file based on `.env.example`
    - Add your API keys:

    ```sh
    HUME_API_KEY=YOUR_HUME_API_KEY
    ANTHROPIC_API_KEY=YOUR_ANTHROPIC_API_KEY
    ELEVENLABS_API_KEY=YOUR_ELEVENLABS_API_KEY
    ```

4. Run the application:

    ```sh
    watchfiles "python -m src.app"`
    ```

## User Flow

1. **Enter or Generate Text:** Type directly in the Text box, or optionally enter a Prompt, click "Generate text", and edit if needed.
2. **Synthesize Speech:** Click "Synthesize speech" to generate two audio outputs.
3. **Listen & Compare:** Playback both options (A & B) to hear the differences.
4. **Vote for Your Favorite:** Click "Vote for option A" or "Vote for option B" to choose your favorite.

## License
[Add your chosen license here]
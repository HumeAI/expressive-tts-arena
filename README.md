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
- pip >=25.0
- Virtual environment capability
- API keys for Hume AI, Anthropic, and ElevenLabs
- For a complete list of dependencies, see requirements.

## Project Structure
```
Expressive TTS Arena/
├── src/
│   ├── integrations/
│   │   ├── __init__.py         # Makes integrations a package; exposes API clients
│   │   ├── anthropic_api.py    # Anthropic API integration
│   │   ├── elevenlabs_api.py   # ElevenLabs API integration
│   │   └── hume_api.py         # Hume API integration
│   ├── __init__.py             # Makes src a package; exposes key functionality
│   ├── app.py                  # Entry file
│   ├── config.py               # Global config and logger setup
│   ├── constants.py            # Global constants
│   ├── theme.py                # Custom Gradio Theme
│   └── utils.py                # Utility functions
├── .env.example
├── .gitignore
├── .pre-commit-config.yaml
└── requirements.txt
```

## Installation

1. Create and activate the virtual environment:

    Mac/Linux
    ```sh
    python -m venv gradio-env
    source gradio-env/bin/activate
    ```

    Windows
    ```sh
    python -m venv gradio-env
    gradio-env\Scripts\activate
    ```

2. Install dependencies:
    ```sh
    pip install -r requirements.txt
    ```

3. (Optional) If contributing, install pre-commit hook for automatic file formatting:
    ```sh
    pre-commit install
    ```

4. Configure environment variables:
    - Create a `.env` file based on `.env.example`
    - Add your API keys:

    ```sh
    HUME_API_KEY=YOUR_HUME_API_KEY
    ANTHROPIC_API_KEY=YOUR_ANTHROPIC_API_KEY
    ELEVENLABS_API_KEY=YOUR_ELEVENLABS_API_KEY
    ```

5. Run the application:
    ```sh
    watchfiles "python -m src.app"
    ```

6. Test the application by navigating to the the localhost URL in your browser (e.g. localhost:7860 or http://127.0.0.1:7860)

## User Flow

1. **Enter or Generate Text:** Type directly in the Text box, or optionally enter a Prompt, click "Generate text", and edit if needed.
2. **Synthesize Speech:** Click "Synthesize speech" to generate two audio outputs.
3. **Listen & Compare:** Playback both options (A & B) to hear the differences.
4. **Vote for Your Favorite:** Click "Vote for option A" or "Vote for option B" to choose your favorite.

## License
This project is licensed under the MIT License - see the [LICENSE.txt](LICENSE.txt) file for details.
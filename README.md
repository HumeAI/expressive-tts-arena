<div align="center">
    <img src="https://storage.googleapis.com/hume-public-logos/hume/hume-banner.png">
    <h1>Hume AI | Expressive TTS Arena</h1>
    <p>
        <strong> An interactive platform for comparing and evaluating the expressiveness of different text-to-speech models </strong>
    </p>
</div>

## Overview

Expressive TTS Arena is an open-source web application that enables users to compare text-to-speech outputs with a focus on expressiveness rather than just audio quality. Built with [Gradio](https://www.gradio.app/), it provides a seamless interface for generating and comparing speech synthesis from different providers, including Hume AI and ElevenLabs.

## Features

- Text generation using Claude 3.5 Sonnet by Anthropic for creating expressive content.
- Direct text input or AI-assisted text generation.
- Comparative analysis of different TTS outputs.
- Simple voting mechanism for preferred outputs.

## Prerequisites

- Python >=3.11.11
- pip >=25.0
- Virtual environment capability
- API keys for Hume AI, Anthropic, and ElevenLabs
- For a complete list of dependencies, see [requirements.txt](./requirements.txt).

## Project Structure

```
Expressive TTS Arena/
├── src/
│   ├── assets/
│   │   ├── styles.css          # Defines custom css
│   ├── database/
│   │   ├── __init__.py         # Makes database a package; expose ORM methods
│   │   ├── crud.py             # Defines operations for interacting with database
│   │   ├── database.py         # Sets up SQLAlchemy database connection
│   │   └── models.py           # SQLAlchemy database models
│   ├── integrations/
│   │   ├── __init__.py         # Makes integrations a package; exposes API clients
│   │   ├── anthropic_api.py    # Anthropic API integration
│   │   ├── elevenlabs_api.py   # ElevenLabs API integration
│   │   └── hume_api.py         # Hume API integration
│   ├── scripts/
│   │   ├── __init__.py         # Makes scripts a package
│   │   ├── init_db.py          # Script for initializing database
│   │   ├── test_db.py          # Script for testing database connection
│   ├── __init__.py             # Makes src a package
│   ├── app.py                  # Entry file
│   ├── config.py               # Global config and logger setup
│   ├── constants.py            # Global constants
│   ├── custom_types.py         # Global custom types
│   ├── theme.py                # Custom Gradio Theme
│   └── utils.py                # Utility functions
│── static/
│   ├── audio/                  # Directory for storing generated audio files
├── .env.example
├── .gitignore
├── .pre-commit-config.yaml
├── Dockerfile
├── LICENSE.txt
├── pyproject.toml
├── README.md
├── uv.lock
```

## Installation

1. This project uses the [uv](https://docs.astral.sh/uv/) package manager. Follow the installation instructions for your platform [here](https://docs.astral.sh/uv/getting-started/installation/).

2. Configure environment variables:
    - Create a `.env` file based on `.env.example`
    - Add your API keys:

    ```txt
    HUME_API_KEY=YOUR_HUME_API_KEY
    ANTHROPIC_API_KEY=YOUR_ANTHROPIC_API_KEY
    ELEVENLABS_API_KEY=YOUR_ELEVENLABS_API_KEY
    ```

3. Run the application:

    Standard
    ```sh
    uv run python -m src.app
    ```

    With hot-reloading
    ```sh
    uv run watchfiles "python -m src.app" src
    ```

4. Test the application by navigating to the the localhost URL in your browser (e.g. `localhost:7860` or `http://127.0.0.1:7860`)

5. (Optional) If contributing, install pre-commit hook for automatic file formatting:
    ```sh
    uv run pre-commit install
    ```

## User Flow

1. **Enter or Generate Text:** Type directly in the Text box, or optionally enter a Character description, click "Generate text", and edit if needed.
2. **Synthesize Speech:** Click "Synthesize speech" to generate two audio outputs.
3. **Listen & Compare:** Playback both options (A & B) to hear the differences.
4. **Vote for Your Favorite:** Click "Vote for option A" or "Vote for option B" to choose your favorite.

## License

This project is licensed under the MIT License - see the [LICENSE.txt](LICENSE.txt) file for details.

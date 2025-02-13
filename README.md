<div align="center">
    <img src="https://storage.googleapis.com/hume-public-logos/hume/hume-banner.png">
    <h1>Expressive TTS Arena</h1>
    <p>
        <strong> An web application for comparing and evaluating the expressiveness of different text-to-speech models </strong>
    </p>
</div>

## Overview

Expressive TTS Arena is an open-source web application that enables users to compare text-to-speech outputs with a focus on expressiveness rather than just audio quality. Built with [Gradio](https://www.gradio.app/), it provides a seamless interface for generating and comparing speech synthesis from different providers, including Hume AI and ElevenLabs.

## Prerequisites

- [Python >=3.11.11](https://www.python.org/downloads/)
- [pip >=25.0](https://pypi.org/project/pip/)
- [uv >=0.5.29](https://github.com/astral-sh/uv)
- [Postgres](https://www.postgresql.org/download/)
- API keys for Hume AI, Anthropic, and ElevenLabs

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
    uv run python -m src.main
    ```

    With hot-reloading
    ```sh
    uv run watchfiles "python -m src.main" src
    ```

4. Test the application by navigating to the the localhost URL in your browser (e.g. `localhost:7860` or `http://127.0.0.1:7860`)

5. (Optional) If contributing, install pre-commit hook for automatic file formatting:
    ```sh
    uv run pre-commit install
    ```

## User Flow

1. **Choose or enter a character description**: Select a sample from the list or enter your own to guide text and voice generation.
2. **Generate text**: Click **"Generate Text"** to create dialogue based on the character. The generated text will appear in the input field automatically—edit it if needed.
3. **Synthesize speech**: Click **"Synthesize Speech"** to send your text and character description to two TTS APIs. Each API generates a voice and synthesizes speech in that voice.
4. **Listen & compare**: Play both audio options and assess their expressiveness.
5. **Vote for the best**: Click **"Select Option A"** or **"Select Option B"** to choose the most expressive output.

## License

This project is licensed under the MIT License - see the [LICENSE.txt](LICENSE.txt) file for details.

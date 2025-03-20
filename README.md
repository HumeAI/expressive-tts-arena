---
title: Expressive TTS Arena
emoji: 🎤
colorFrom: indigo
colorTo: gray
sdk: docker
app_file: src/main.py
python_version: "3.11"
pinned: true
license: mit
---

<div align="center">
    <img src="https://storage.googleapis.com/hume-public-logos/hume/hume-banner.png">
    <h1>Expressive TTS Arena</h1>
    <p>
        <strong> A web application for comparing and evaluating the expressiveness of different text-to-speech models </strong>
    </p>
</div>

## Overview

Expressive TTS Arena is an open-source web application for evaluating the expressiveness of voice generation and speech synthesis from different text-to-speech providers, including Hume AI and Elevenlabs.

For support or to join the conversation, visit our [Discord](https://discord.com/invite/humeai).

## Prerequisites

- [Python >=3.11.11](https://www.python.org/downloads/)
- [pip >=25.0](https://pypi.org/project/pip/)
- [uv >=0.5.29](https://github.com/astral-sh/uv)
- [Postgres](https://www.postgresql.org/download/)
- API keys for Hume AI, Anthropic, and ElevenLabs

## Project Structure

```
Expressive TTS Arena/
├── public/                     # Directory for public assets
├── src/                        
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
│   ├── config.py               # Global config and logger setup
│   ├── constants.py            # Global constants
│   ├── custom_types.py         # Global custom types
│   ├── frontend.py             # Gradio UI components
│   ├── main.py                 # Entry file
│   └── utils.py                # Utility functions
│── static/
│   ├── audio/                  # Directory for storing generated audio files
│   ├── css/
│   │   ├── styles.css          # Defines custom css
├── .dockerignore
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

5. (Optional) If contributing, install pre-commit hook for automatic linting, formatting, and type-checking:
    ```sh
    uv run pre-commit install
    ```

## User Flow

1. Select a sample character, or input a custom character description and click **"Generate Text"**, to generate your text input.
2. Click the **"Synthesize Speech"** button to synthesize two TTS outputs based on your text and character description.
3. Listen to both audio samples to compare their expressiveness.
4. Vote for the most expressive result by clicking either **"Select Option A"** or **"Select Option B"**.

## License

This project is licensed under the MIT License - see the [LICENSE.txt](LICENSE.txt) file for details.

---
title: Expressive TTS Arena
emoji: 🎤
colorFrom: indigo
colorTo: pink
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
        <strong> 
            A web application for comparing and evaluating the expressiveness of different text-to-speech models 
        </strong>
    </p>
</div>

## Overview

Expressive TTS Arena is an open-source web application for evaluating the expressiveness of voice generation and speech synthesis from different text-to-speech providers.

For support or to join the conversation, visit our [Discord](https://discord.com/invite/humeai).

## Prerequisites

- [Python >=3.11.11](https://www.python.org/downloads/)
- [pip >=25.0](https://pypi.org/project/pip/)
- [uv >=0.5.29](https://github.com/astral-sh/uv)
- [Postgres](https://www.postgresql.org/download/)
- API keys for Hume AI, Anthropic, OpenAI, and ElevenLabs

## Project Structure

```
Expressive TTS Arena/
├── public/
├── src/
│   ├── common/
│   │   ├── __init__.py
│   │   ├── common_types.py         # Application-wide custom type aliases and definitions.
│   │   ├── config.py               # Manages application config (Singleton) loaded from env vars.
│   │   ├── constants.py            # Application-wide constant values.
│   │   ├── utils.py                # General-purpose utility functions used across modules.
│   ├── core/
│   │   ├── __init__.py
│   │   ├── tts_service.py          # Service handling Text-to-Speech provider selection and API calls.
│   │   ├── voting_service.py       # Service managing database operations for votes and leaderboards.
│   ├── database/                   # Database access layer using SQLAlchemy.
│   │   ├── __init__.py
│   │   ├── crud.py                 # Data Access Objects (DAO) / CRUD operations for database models.
│   │   ├── database.py             # Database connection setup (engine, session management).
│   │   └── models.py               # SQLAlchemy ORM models defining database tables.
│   ├── frontend/
│   │   ├── components/
│   │   │   │   ├── __init__.py     
│   │   │   │   ├── arena.py        # UI definition and logic for the 'Arena' tab.
│   │   │   │   ├── leaderboard.py  # UI definition and logic for the 'Leaderboard' tab.
│   │   ├── __init__.py
│   │   ├── frontend.py             # Main Gradio application class; orchestrates UI components and layout.
│   ├── integrations/               # Modules for interacting with external third-party APIs.
│   │   ├── __init__.py
│   │   ├── anthropic_api.py        # Integration logic for the Anthropic API.
│   │   ├── elevenlabs_api.py       # Integration logic for the ElevenLabs API.
│   │   └── hume_api.py             # Integration logic for the Hume API.
│   ├── middleware/
│   │   ├── __init__.py
│   │   ├── meta_tag_injection.py   # Middleware for injecting custom HTML meta tags into the Gradio page.
│   ├── scripts/
│   │   ├── __init__.py
│   │   ├── init_db.py              # Script to create database tables based on models.
│   │   ├── test_db.py              # Script for testing the database connection configuration.
│   ├── __init__.py
│   ├── main.py                     # Main script to configure and run the Gradio application.
│── static/
│   ├── audio/                      # Temporary storage for generated audio files served to the UI.
│   ├── css/
│   │   ├── styles.css              # Custom CSS overrides and styling for the Gradio UI.
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
    OPENAI_API_KEY=YOUR_OPENAI_API_KEY
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

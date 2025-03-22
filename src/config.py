"""
config.py

Global configuration and logger setup for the project.

Key Features:
- Uses environment variables defined in the system (Docker in production).
- Loads a `.env` file only in development to simulate production variables locally.
- Configures the logger for consistent logging across all modules.
- Dynamically enables DEBUG logging in development and INFO logging in production (unless overridden).
"""

# Standard Library Imports
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, Optional

# Third-Party Library Imports
from dotenv import load_dotenv

# Local Application Imports
if TYPE_CHECKING:
    from src.integrations import AnthropicConfig, ElevenLabsConfig, HumeConfig, OpenAIConfig

logger: logging.Logger = logging.getLogger("expressive_tts_arena")


@dataclass(frozen=True)
class Config:
    _config: ClassVar[Optional["Config"]] = None
    app_env: str
    debug: bool
    database_url: Optional[str]
    audio_dir: Path
    anthropic_config: "AnthropicConfig"
    hume_config: "HumeConfig"
    elevenlabs_config: "ElevenLabsConfig"
    openai_config: "OpenAIConfig"

    @classmethod
    def get(cls) -> "Config":
        if cls._config:
            return cls._config

        _config = Config._init()
        cls._config = _config
        return _config

    @staticmethod
    def _init():
        app_env = os.getenv("APP_ENV", "dev").lower()
        if app_env not in {"dev", "prod"}:
            app_env = "dev"

        # In development, load environment variables from .env file (not used in production)
        if app_env == "dev" and Path(".env").exists():
            load_dotenv(".env", override=True)

        # Enable debug mode if in development (or if explicitly set in env variables)
        debug = app_env == "dev" or os.getenv("DEBUG", "false").lower() == "true"

        database_url = os.getenv("DATABASE_URL")

        # Configure the logger
        logging.basicConfig(
            level=logging.DEBUG if debug else logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        logger.info(f'App running in "{app_env}" mode.')
        logger.info(f"Debug mode is {'enabled' if debug else 'disabled'}.")

        # Define the directory for audio files relative to the project root
        audio_dir = Path.cwd() / "static" / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Audio directory set to {audio_dir}")

        if debug:
            logger.debug("DEBUG mode enabled.")

        from src.integrations import AnthropicConfig, ElevenLabsConfig, HumeConfig, OpenAIConfig

        return Config(
            app_env=app_env,
            debug=debug,
            database_url=database_url,
            audio_dir=audio_dir,
            anthropic_config=AnthropicConfig(),
            hume_config=HumeConfig(),
            elevenlabs_config=ElevenLabsConfig(),
            openai_config=OpenAIConfig(),
        )

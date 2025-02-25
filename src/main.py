"""
main.py

This module is the entry point for the app. It loads configuration and starts the Gradio app.
"""

# Standard Library Imports
import asyncio

# Local Application Imports
from src.app import App
from src.config import Config, logger
from src.database import init_db


async def main():
    """
    Asynchronous main function to initialize the application.
    """
    config = Config.get()
    logger.info("Launching TTS Arena Gradio app...")
    db_session_maker = init_db(config)
    app = App(config, db_session_maker)
    demo = app.build_gradio_interface()
    demo.launch(
        server_name="0.0.0.0",
        allowed_paths=[str(config.audio_dir)],
        ssl_verify= False,
    )


if __name__ == "__main__":
    asyncio.run(main())

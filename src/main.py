"""
main.py

This module is the entry point for the app. It loads configuration and starts the Gradio app.
"""

from src.app import App
from src.config import Config, logger
from src.database.database import init_db

if __name__ == "__main__":
    config = Config.get()
    logger.info("Launching TTS Arena Gradio app...")
    db_session_maker = init_db(config)
    app = App(config, db_session_maker)
    demo = app.build_gradio_interface()
    init_db(config)
    demo.launch(server_name="0.0.0.0", allowed_paths=[str(config.audio_dir)])

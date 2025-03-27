"""
main.py

This module is the entry point for the app. It loads configuration and starts the Gradio app.
"""

# Standard Library Imports
import asyncio
from pathlib import Path

# Third-Party Library Imports
import gradio as gr
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

# Local Application Imports
from src.common.config import Config, logger
from src.database import init_db
from src.frontend import Frontend
from src.middleware import MetaTagInjectionMiddleware


async def main():
    """
    Asynchronous main function to initialize the application.
    """
    logger.info("Launching TTS Arena Gradio app...")
    config = Config.get()
    db_session_maker = init_db(config)

    frontend = Frontend(config, db_session_maker)
    demo = await frontend.build_gradio_interface()

    app = FastAPI()
    app.add_middleware(MetaTagInjectionMiddleware)

    public_dir = Path("public")
    app.mount("/static", StaticFiles(directory=public_dir), name="static")

    gr.mount_gradio_app(
        app=app,
        blocks=demo,
        path="/",
        allowed_paths=["static"]
    )

    import uvicorn
    config = uvicorn.Config(app, host="0.0.0.0", port=7860, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())

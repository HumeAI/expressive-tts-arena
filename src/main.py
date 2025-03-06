"""
main.py

This module is the entry point for the app. It loads configuration and starts the Gradio app.
"""

# Standard Library Imports
import asyncio
from pathlib import Path
from typing import Awaitable, Callable

# Third-Party Library Imports
import gradio as gr
from fastapi import FastAPI, Request
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from src.config import Config, logger
from src.constants import META_TAGS
from src.database import init_db

# Local Application Imports
from src.frontend import Frontend
from src.utils import update_meta_tags


class ResponseModifierMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware that safely intercepts and modifies the HTML response from the root endpoint
    to inject custom meta tags into the document head.

    This middleware specifically targets the root path ('/') and leaves all other endpoint
    responses unmodified. It uses BeautifulSoup to properly parse and modify the HTML,
    ensuring that JavaScript functionality remains intact.
    """
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # Process the request and get the response
        response = await call_next(request)

        # Only intercept responses from the root endpoint and HTML content
        if request.url.path == "/" and response.headers.get("content-type", "").startswith("text/html"):
            # Get the response body
            response_body = b""
            async for chunk in response.body_iterator:
                response_body += chunk

            try:
                # Decode, modify, and re-encode the content
                content = response_body.decode("utf-8")
                modified_content = update_meta_tags(content, META_TAGS).encode("utf-8")

                # Update content-length header to reflect modified content size
                headers = dict(response.headers)
                headers["content-length"] = str(len(modified_content))

                # Create a new response with the modified content
                return Response(
                    content=modified_content,
                    status_code=response.status_code,
                    headers=headers,
                    media_type=response.media_type
                )
            except Exception:
                # If there's an error, return the original response
                return Response(
                    content=response_body,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type
                )

        return response


async def main():
    """
    Asynchronous main function to initialize the application.
    """
    logger.info("Launching TTS Arena Gradio app...")
    config = Config.get()
    db_session_maker = init_db(config)

    frontend = Frontend(config, db_session_maker)
    demo = frontend.build_gradio_interface()

    app = FastAPI()
    app.add_middleware(ResponseModifierMiddleware)

    assets_dir = Path("src/assets")
    app.mount("/static", StaticFiles(directory=assets_dir), name="static")

    gr.mount_gradio_app(
        app=app,
        blocks=demo,
        path="/",
        allowed_paths=[str(config.audio_dir), "src/assets"]
    )

    import uvicorn
    config = uvicorn.Config(app, host="0.0.0.0", port=7860, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())

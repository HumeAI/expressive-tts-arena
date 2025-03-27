"""
meta_tag_injection.py

This module contains middleware that injects metatags into responses from the FastAPI application by injecting meta
tags into HTML responses.
"""

# Standard Library Imports
from typing import Awaitable, Callable, Dict, List

# Third-Party Library Imports
from bs4 import BeautifulSoup
from fastapi import Request
from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware

# HTML and social media metadata for the Gradio application
# These tags define SEO-friendly content and provide rich previews when shared on social platforms
META_TAGS: List[Dict[str, str]] = [
    # HTML Meta Tags (description)
    {
        'name': 'description',
        'content': 'An open-source web application for comparing and evaluating the expressiveness of different text-to-speech models, including Hume AI and ElevenLabs.'
    },
    # Facebook Meta Tags
    {
        'property': 'og:url',
        'content': 'https://hume.ai'
    },
    {
        'property': 'og:type',
        'content': 'website'
    },
    {
        'property': 'og:title',
        'content': 'Expressive TTS Arena'
    },
    {
        'property': 'og:description',
        'content': 'An open-source web application for comparing and evaluating the expressiveness of different text-to-speech models, including Hume AI and ElevenLabs.'
    },
    {
        'property': 'og:image',
        'content': '/static/arena-opengraph-logo.png'
    },
    # Twitter Meta Tags
    {
        'name': 'twitter:card',
        'content': 'summary_large_image'
    },
    {
        'property': 'twitter:domain',
        'content': 'hume.ai'
    },
    {
        'property': 'twitter:url',
        'content': 'https://hume.ai'
    },
    {
        'name': 'twitter:creator',
        'content': '@hume_ai'
    },
    {
        'name': 'twitter:title',
        'content': 'Expressive TTS Arena'
    },
    {
        'name': 'twitter:description',
        'content': 'An open-source web application for comparing and evaluating the expressiveness of different text-to-speech models, including Hume AI and ElevenLabs.'
    },
    {
        'name': 'twitter:image',
        'content': '/static/arena-opengraph-logo.png'
    }
]


def __update_meta_tags(html_content: str, meta_tags: List[Dict[str, str]]) -> str:
    """
    Safely updates the HTML content by adding or replacing meta tags in the head section
    without affecting other elements, especially scripts and event handlers.

    Args:
        html_content: The original HTML content as a string
        meta_tags: A list of dictionaries with meta tag attributes to add

    Returns:
        The modified HTML content with updated meta tags
    """
    # Parse the HTML
    soup = BeautifulSoup(html_content, 'html.parser')
    head = soup.head

    # Remove existing meta tags that would conflict with our new ones
    for meta_tag in meta_tags:
        # Determine if we're looking for 'name' or 'property' attribute
        attr_type = 'name' if 'name' in meta_tag else 'property'
        attr_value = meta_tag.get(attr_type)

        # Find and remove existing meta tags with the same name/property
        existing_tags = head.find_all('meta', attrs={attr_type: attr_value})
        for tag in existing_tags:
            tag.decompose()

    # Add the new meta tags to the head section
    for meta_info in meta_tags:
        new_meta = soup.new_tag('meta')
        for attr, value in meta_info.items():
            new_meta[attr] = value
        head.append(new_meta)

    return str(soup)


class MetaTagInjectionMiddleware(BaseHTTPMiddleware):
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
                modified_content = __update_meta_tags(content, META_TAGS).encode("utf-8")

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

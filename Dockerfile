# Use the official Python 3.11 slim image as the base image
FROM python:3.11-slim

# Install curl (if not already present) and install uv using its standalone installer
RUN apt-get update && apt-get install -y curl && \
    curl -LsSf https://astral.sh/uv/install.sh | sh && \
    rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy all project files into the container
COPY . .

# Pre-sync the project’s virtual environment and install dependencies
# This command reads your pyproject.toml (and uv.lock if available) and creates a .venv with all required packages.
RUN /root/.local/bin/uv sync

# Gradio port 7860
EXPOSE 7860

# Define the command to run your application using uv.
# uv run will automatically ensure that the built-in venv is active and dependencies are up to date.
CMD ["/root/.local/bin/uv", "run", "python", "-m", "src.app"]

# Use the official lightweight Python 3.11 slim image as the base
FROM python:3.11-slim

# Set up a non-root user for improved security
RUN useradd -m -u 1000 user

# Create app directory and set proper ownership
RUN mkdir -p /app && chown -R user:user /app

# Install uv and required system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl libpq-dev gcc build-essential && \
    mkdir -p /home/user/.local/bin && \
    curl -LsSf https://astral.sh/uv/install.sh | sh && \
    cp /root/.local/bin/uv /usr/local/bin/ && \
    cp /root/.local/bin/uvx /usr/local/bin/ && \
    chmod +x /usr/local/bin/uv /usr/local/bin/uvx && \
    chown -R user:user /home/user/.local && \
    apt-get remove -y curl && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Switch to the non-root user
USER user

# Set environment variables for the user
ENV HOME=/home/user \
    PATH="/home/user/.local/bin:/usr/local/bin:$PATH"

# Set the working directory in the container
WORKDIR /app

# Copy dependency files first with proper ownership
COPY --chown=user pyproject.toml uv.lock /app/

# Install dependencies using uv
#   - Reads pyproject.toml (and uv.lock, if available) to install dependencies
#   - Creates a .venv in the project directory with all required packages
RUN uv sync

# Copy the remaining project files into the container with proper ownership
COPY --chown=user . .

# Document the port used by Gradio
EXPOSE 7860

# Define the command to start the application
#   - `uv run` ensures that the virtual environment is activated and dependencies are up to date
#   - `python -m src.main` runs the main application module
CMD ["uv", "run", "python", "-m", "src.main"]
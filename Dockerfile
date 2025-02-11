# Use the official lightweight Python 3.11 slim image as the base
FROM python:3.11-slim

# Install uv using its standalone installer
#   - `apt-get update` fetches the latest package lists
#   - `apt-get install -y --no-install-recommends curl` installs curl to fetch the uv installer
#   - `curl -LsSf` downloads and runs the uv installer script
#   - `apt-get remove -y curl` removes curl after installation to save space
#   - `apt-get clean && rm -rf /var/lib/apt/lists/*` removes cached package lists to reduce image size
RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    curl -LsSf https://astral.sh/uv/install.sh | sh && \
    apt-get remove -y curl && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Add uv to the system PATH so it can be run globally
ENV PATH="/root/.local/bin:$PATH"

# Set the working directory in the container
WORKDIR /app

# Copy dependency files first (pyproject.toml & uv.lock) to leverage Docker’s build cache
#   - Ensures that if only the application code changes, dependencies do not need to be reinstalled
COPY pyproject.toml uv.lock /app/

# Install dependencies using uv
#   - Reads pyproject.toml (and uv.lock, if available) to install dependencies
#   - Creates a .venv in the project directory with all required packages
RUN uv sync

# Copy the remaining project files into the container
COPY . .

# Document the port used by Gradio (optional)
#   - This does not actually expose the port, it is just metadata for users
#   - To actually expose the port, use `docker run -p 7860:7860 <image>`
EXPOSE 7860

# Define the command to start the application
#   - `uv run` ensures that the virtual environment is activated and dependencies are up to date
#   - `python -m src.app` runs the main application module
CMD ["uv", "run", "python", "-m", "src.app"]

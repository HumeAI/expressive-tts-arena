# Use the official lightweight Python 3.11 slim image as the base
FROM python:3.11-slim

# Set up a new user named "user" with user ID 1000
RUN useradd -m -u 1000 user

# Switch to the "user" user
USER user

# Set home to the user's home directory
ENV HOME=/home/user \
	PATH=/root/.local/bin:/home/user/.local/bin:$PATH

# Set the working directory to the user's home directory
WORKDIR $HOME/app

# Install uv and required system dependencies
#   - `apt-get update` fetches the latest package lists
#   - `apt-get install -y --no-install-recommends curl libpq-dev gcc build-essential` installs:
#       - curl: to fetch the uv installer script
#       - libpq-dev: provides pg_config required by psycopg2
#       - gcc & build-essential: required for compiling C extensions (e.g. psycopg2)
#   - `curl -LsSf` downloads and runs the uv installer script
#   - `apt-get remove -y curl` removes curl after installation to save space
#   - `apt-get clean && rm -rf /var/lib/apt/lists/*` removes cached package lists to reduce image size
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl libpq-dev gcc build-essential && \
    curl -LsSf https://astral.sh/uv/install.sh | sh && \
    apt-get remove -y curl && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy dependency files first (pyproject.toml & uv.lock) to leverage Docker’s build cache
#   - Ensures that if only the application code changes, dependencies do not need to be reinstalled
COPY pyproject.toml uv.lock /app/

# Install dependencies using uv
#   - Reads pyproject.toml (and uv.lock, if available) to install dependencies
#   - Creates a .venv in the project directory with all required packages
RUN uv sync

# Copy the remaining project files into the container
COPY . .

# Document the port used by Gradio
#   - This does not actually expose the port, it is just metadata for users
#   - To actually expose the port, use `docker run -p 7860:7860 <image>`
EXPOSE 7860

# Define the command to start the application
#   - `uv run` ensures that the virtual environment is activated and dependencies are up to date
#   - `python -m src.main` runs the main application module
CMD ["uv", "run", "python", "-m", "src.main"]
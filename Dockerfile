# Use the official lightweight Python 3.11 slim image with explicit platform
FROM python:3.11-slim

# Install required system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl libpq-dev gcc build-essential file && \
    # Download the uv binary directly from GitHub releases
    curl -L https://github.com/astral-sh/uv/releases/download/0.6.2/uv-x86_64-unknown-linux-gnu.tar.gz -o /tmp/uv.tar.gz && \
    # Create directory for extraction
    mkdir -p /root/.local/bin && \
    # Extract the tarball
    tar -xzf /tmp/uv.tar.gz && \
    # Move the binary to the desired location
    mv ./uv-x86_64-unknown-linux-gnu/uv /root/.local/bin/uv && \
    # Make the binary executable
    chmod +x /root/.local/bin/uv && \
    # Verify the binary architecture
    file /root/.local/bin/uv && \
    # Clean up
    rm /tmp/uv.tar.gz && \
    apt-get remove -y curl && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Add uv to the system PATH so it can be run globally
ENV PATH="/root/.local/bin:$PATH"

# Set the working directory in the container
WORKDIR /app

# Copy dependency files first to leverage Docker's build cache
COPY pyproject.toml uv.lock /app/

# Install dependencies using uv
RUN uv sync

# Copy the remaining project files into the container
COPY . .

# Document the port used by Gradio
EXPOSE 7860

# Define the command to start the application
CMD ["uv", "run", "python", "-m", "src.main"]

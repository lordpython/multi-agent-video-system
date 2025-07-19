# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Multi-Agent Video System Docker Image
# Based on ADK deployment patterns with video processing capabilities

FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV DEBIAN_FRONTEND=noninteractive

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    # FFmpeg for video processing
    ffmpeg \
    # Image processing libraries
    libimage-exiftool-perl \
    imagemagick \
    # Audio processing
    sox \
    libsox-fmt-all \
    # Network tools
    curl \
    wget \
    # Build tools (needed for some Python packages)
    build-essential \
    pkg-config \
    # Git (for version control)
    git \
    # Clean up
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Verify FFmpeg installation
RUN ffmpeg -version

# Install Poetry for dependency management
RUN pip install --no-cache-dir poetry==1.8.3

# Configure Poetry
ENV POETRY_NO_INTERACTION=1
ENV POETRY_VENV_IN_PROJECT=1
ENV POETRY_CACHE_DIR=/tmp/poetry_cache

# Copy Poetry configuration files
COPY pyproject.toml poetry.lock ./

# Install Python dependencies
RUN poetry install --only=main --no-root && rm -rf $POETRY_CACHE_DIR

# Create necessary directories
RUN mkdir -p \
    /app/logs \
    /app/output \
    /app/temp \
    /app/cache/assets \
    /app/data/sessions \
    /app/test_data

# Copy application code
COPY . .

# Install the application
RUN poetry install --only-root

# Create non-root user for security
RUN groupadd -r videouser && useradd -r -g videouser videouser

# Set ownership of application directories
RUN chown -R videouser:videouser /app

# Switch to non-root user
USER videouser

# Set default environment variables
ENV LOG_LEVEL=INFO
ENV LOG_DIR=/app/logs
ENV VIDEO_OUTPUT_DIR=/app/output
ENV TEMP_DIR=/app/temp
ENV ASSET_CACHE_DIR=/app/cache/assets
ENV SESSION_DATA_DIR=/app/data/sessions
ENV FFMPEG_PATH=/usr/bin/ffmpeg
ENV ENVIRONMENT=production
ENV ENABLE_STRUCTURED_LOGGING=true

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from video_system.shared_libraries.config_manager import validate_system_configuration; exit(0 if not validate_system_configuration() else 1)"

# Expose ports
EXPOSE 8000

# Default command
CMD ["poetry", "run", "python", "video_cli.py", "--help"]
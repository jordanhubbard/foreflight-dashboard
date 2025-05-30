# syntax=docker/dockerfile:1.4

# Build arguments
ARG PYTHON_VERSION=3.11
ARG BUILDKIT_INLINE_CACHE=1
ARG FLASK_DEBUG=1
ARG FLASK_ENV=development

# Base stage with common dependencies
FROM python:${PYTHON_VERSION}-slim AS base
WORKDIR /app

# Set environment variables
ENV PYTHONPATH=/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Copy entrypoint script
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Create necessary directories
RUN mkdir -p uploads logs

# Copy requirements first for better caching
COPY requirements.txt .

# Development stage with testing tools
FROM base AS development

# Pass build arguments to environment
ARG FLASK_DEBUG
ARG FLASK_ENV
ENV FLASK_DEBUG=${FLASK_DEBUG} \
    FLASK_ENV=${FLASK_ENV}

# Install development and testing dependencies
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install pytest pytest-cov flake8 black isort

# Install application dependencies
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# Copy the application code
COPY . .

# Set Flask app environment variable
ENV FLASK_APP=src/app.py

# Expose ports for Flask and FastAPI
EXPOSE 5050 5051

# Use the entrypoint script
ENTRYPOINT ["/docker-entrypoint.sh"]

# Testing stage for running tests
FROM development AS testing

# Set testing environment variables
ENV FLASK_DEBUG=0 \
    FLASK_ENV=testing

# Default command for testing
CMD ["pytest", "tests/", "-v"]

# Production stage - optimized for smaller size and security
FROM base AS production

# Pass build arguments to environment
ARG FLASK_DEBUG=0
ARG FLASK_ENV=production
ENV FLASK_DEBUG=${FLASK_DEBUG} \
    FLASK_ENV=${FLASK_ENV}

# Install only production dependencies
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# Copy only necessary files for production
COPY src/ /app/src/
COPY docker-entrypoint.sh /docker-entrypoint.sh

# Set Flask app environment variable
ENV FLASK_APP=src/app.py

# Expose ports for Flask and FastAPI
EXPOSE 5050 5051

# Use the entrypoint script
ENTRYPOINT ["/docker-entrypoint.sh"]

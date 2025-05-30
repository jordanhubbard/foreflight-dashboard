# syntax=docker/dockerfile:1.4

# Base stage with common dependencies
FROM python:3.11-slim AS base
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

# Install development and testing dependencies
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install pytest pytest-cov flake8 black isort

# Install application dependencies
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# Copy the application code
COPY . .

# Set development environment variables
ENV FLASK_APP=src/app.py \
    FLASK_DEBUG=1 \
    FLASK_ENV=development

# Expose ports for Flask and FastAPI
EXPOSE 5050 5051

# Use the entrypoint script
ENTRYPOINT ["/docker-entrypoint.sh"]

# Production stage - optimized for smaller size and security
FROM base AS production

# Install only production dependencies
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# Copy only necessary files for production
COPY src/ /app/src/
COPY static/ /app/static/

# Set production environment variables
ENV FLASK_APP=src/app.py \
    FLASK_DEBUG=0 \
    FLASK_ENV=production

# Expose ports for Flask and FastAPI
EXPOSE 5050 5051

# Use the entrypoint script
ENTRYPOINT ["/docker-entrypoint.sh"]

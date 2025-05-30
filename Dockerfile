FROM python:3.11-slim

WORKDIR /app

# Install development and testing dependencies
RUN pip install --no-cache-dir pytest pytest-cov flake8 black isort

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy entrypoint script first
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Copy the rest of the application
COPY . .

# Create necessary directories
RUN mkdir -p uploads logs

# Expose ports for Flask and FastAPI
EXPOSE 5050 5051

# Set environment variables
ENV PYTHONPATH=/app
ENV FLASK_APP=src/app.py
ENV FLASK_DEBUG=1
ENV FLASK_ENV=development

# Use the entrypoint script
ENTRYPOINT ["/docker-entrypoint.sh"]

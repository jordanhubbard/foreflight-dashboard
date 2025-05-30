FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

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

# Command to run the application
CMD ["sh", "-c", "python -m flask run --host=0.0.0.0 --port=5050 & python -m uvicorn src.api.routes:app --host=0.0.0.0 --port=5051 & wait"]

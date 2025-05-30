#!/bin/bash
set -e

# Create necessary directories
mkdir -p uploads logs

# Start Flask application in background
echo "Starting Flask application..."
python -m flask run --host=0.0.0.0 --port=5050 &
FLASK_PID=$!

# Start FastAPI application in background
echo "Starting FastAPI application..."
python -m uvicorn src.api.routes:app --host=0.0.0.0 --port=5051 &
UVICORN_PID=$!

# Handle shutdown signals
trap 'kill $FLASK_PID $UVICORN_PID; exit 0' SIGTERM SIGINT

# Keep the script running
echo "Services started. Press Ctrl+C to stop."
wait $FLASK_PID $UVICORN_PID

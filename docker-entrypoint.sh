#!/bin/bash
set -e

# Create necessary directories
mkdir -p uploads logs

# Check if we're running pytest
if [[ "$1" == "pytest" ]]; then
    echo "Running pytest..."
    exec "$@"  # Execute pytest with all arguments
else
    # Start Flask application in background
    echo "Starting Flask application..."
    cd /app
    export PYTHONPATH=/app
    python -m src.app --host=0.0.0.0 --port=5050 &
    FLASK_PID=$!

    # Start FastAPI application in background
    echo "Starting FastAPI application..."
    python -m uvicorn src.api.routes:app --host=0.0.0.0 --port=5051 --reload &
    UVICORN_PID=$!

    # Handle shutdown signals
    trap 'kill $FLASK_PID $UVICORN_PID; exit 0' SIGTERM SIGINT

    # Keep the script running
    echo "Services started. Press Ctrl+C to stop."
    wait $FLASK_PID $UVICORN_PID
fi

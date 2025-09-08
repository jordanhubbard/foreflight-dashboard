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
    python -m src.app --host=0.0.0.0 --port=8081 &
    FLASK_PID=$!

    # Start FastAPI application in background
    echo "Starting FastAPI application..."
    python -m uvicorn src.api.routes:app --host=0.0.0.0 --port=5051 --reload &
    UVICORN_PID=$!

    # In production, React dev server is not needed - Flask serves the built static files
    if [ "$FLASK_ENV" = "development" ] && [ -d "/app/frontend" ]; then
        echo "Starting React development server..."
        cd /app/frontend
        npm install --silent
        npm run dev &
        REACT_PID=$!
        cd /app
    else
        echo "Production mode: Flask will serve built React static files"
        REACT_PID=""
    fi

    # Handle shutdown signals
    if [ -n "$REACT_PID" ]; then
        trap 'kill $FLASK_PID $UVICORN_PID $REACT_PID; exit 0' SIGTERM SIGINT
    else
        trap 'kill $FLASK_PID $UVICORN_PID; exit 0' SIGTERM SIGINT
    fi

    # Keep the script running
    echo "Services started. Press Ctrl+C to stop."
    if [ -n "$REACT_PID" ]; then
        wait $FLASK_PID $UVICORN_PID $REACT_PID
    else
        wait $FLASK_PID $UVICORN_PID
    fi
fi

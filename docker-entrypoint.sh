#!/bin/bash
set -e

# Create necessary directories
mkdir -p uploads logs

# Check if we're running pytest
if [[ "$1" == "pytest" ]]; then
    echo "Running pytest..."
    exec "$@"  # Execute pytest with all arguments
else
    echo "🔥 Starting Modern FastAPI Application (Flask has been eliminated!) 🔥"
    cd /app
    export PYTHONPATH=/app

    # Start FastAPI application (replaces both Flask and old FastAPI)
    echo "Starting FastAPI application on port ${FASTAPI_PORT:-5051}..."
    python -m uvicorn src.main:app --host=0.0.0.0 --port=${FASTAPI_PORT:-5051} --reload &
    FASTAPI_PID=$!

    # In development, start React dev server for hot reloading
    if [ "${ENVIRONMENT:-$FLASK_ENV}" = "development" ] && [ -d "/app/frontend" ]; then
        echo "Starting React development server on port ${REACT_DEV_PORT:-3000}..."
        cd /app/frontend
        npm install --silent
        npm run dev &
        REACT_PID=$!
        cd /app
    else
        echo "Production mode: FastAPI serves built React static files"
        REACT_PID=""
    fi

    # Handle shutdown signals
    if [ -n "$REACT_PID" ]; then
        trap 'kill $FASTAPI_PID $REACT_PID; exit 0' SIGTERM SIGINT
    else
        trap 'kill $FASTAPI_PID; exit 0' SIGTERM SIGINT
    fi

    # Keep the script running
    echo "✅ Services started successfully!"
    if [ -n "$REACT_PID" ]; then
        echo "🎯 PRIMARY UI: http://localhost:${REACT_DEV_PORT:-3001} (React dev server with live reload)"
        echo "🔧 API Backend: http://localhost:${FASTAPI_PORT:-5051} (internal - use UI instead)"
        echo "📚 API Docs: http://localhost:${FASTAPI_PORT:-5051}/docs"
        wait $FASTAPI_PID $REACT_PID
    else
        echo "🌐 FastAPI App: http://localhost:${FASTAPI_PORT:-5051}"
        echo "📚 API Docs: http://localhost:${FASTAPI_PORT:-5051}/docs"
        wait $FASTAPI_PID
    fi
fi

#!/bin/bash

# Exit on error
set -e

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install or upgrade pip
pip install --upgrade pip

# Install requirements
echo "Installing requirements..."
pip install -r requirements.txt

# Create uploads directory if it doesn't exist
mkdir -p uploads

# Run the Flask application
echo "Starting Flask application..."
PYTHONPATH=. FLASK_DEBUG=1 FLASK_ENV=development python3 src/app.py 
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
export FLASK_APP=src/app.py
export FLASK_DEBUG=1
export FLASK_ENV=development
export PYTHONPATH=.

python3 -m flask run --host=0.0.0.0 --port=5050 --reload 
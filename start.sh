#!/bin/bash

# Exit on any error
set -e

# Check if virtual environment exists, if not create it
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
else
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Install dependencies if requirements.txt has been modified
if [ ! -f "venv/installed" ] || [ "requirements.txt" -nt "venv/installed" ]; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
    touch venv/installed
fi

# Initialize database if it doesn't exist
if [ ! -f "app.db" ]; then
    echo "Initializing database..."
    python run.py --init-db
fi

# Update submodules
echo "Updating submodules..."
git submodule update --init --recursive

# Start the application
echo "Starting the application..."
python run.py
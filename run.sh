#!/bin/bash

# PantryPal - Quick start script

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -q -r requirements.txt

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo ""
    echo "WARNING: Please edit .env and add your ANTHROPIC_API_KEY"
    echo ""
fi

# Run the app
echo "Starting PantryPal..."
echo "Open http://localhost:5000 in your browser"
echo ""
python app.py

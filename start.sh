#!/bin/bash

# Navigate to the script's directory
cd "$(dirname "$0")"

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "Virtual environment 'venv' not found!"
    exit 1
fi

# Run the application
python3 main.py

#!/bin/bash

# Get the directory where this script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Change to that directory
cd "$DIR"

# Activate virtual environment
source venv/bin/activate

# Open the app in default browser after a short delay
sleep 2 && open http://127.0.0.1:8080 &

# Run the Flask app
python3 run.py

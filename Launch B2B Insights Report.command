#!/bin/bash

echo "============================================================"
echo "B2B Insights - Report Generator"
echo "============================================================"
echo
echo "Starting application..."

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed or not in PATH"
    echo "Please install Python 3.8 or higher from https://python.org"
    echo "Press Enter to exit..."
    read
    exit 1
fi

# Check if app.py exists in the current directory
if [ ! -f "app.py" ]; then
    echo "ERROR: app.py not found in the same directory as this launcher"
    echo "Please ensure all files are in the same folder"
    echo "Press Enter to exit..."
    read
    exit 1
fi

# Run the main application
python3 app.py

echo
echo "Application closed."
echo "Press Enter to exit..."
read

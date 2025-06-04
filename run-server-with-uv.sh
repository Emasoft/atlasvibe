#!/bin/bash
# Script to run the atlasvibe server with uv

echo "Starting atlasvibe server with uv..."

# Ensure we're in the project directory
cd "$(dirname "$0")"

# Ensure environment is set up
if [ ! -d ".venv" ] || [ ! -f ".python-version" ]; then
    echo "Setting up environment..."
    uv python pin 3.11
    uv venv
    uv sync
    uv pip install poetry
fi

# Create config directory if needed
mkdir -p ~/.atlasvibe
if [ ! -f ~/.atlasvibe/atlasvibe.yaml ]; then
    echo "LOG_LEVEL: INFO" > ~/.atlasvibe/atlasvibe.yaml
fi

# Run the server with uv
echo "Python version: $(uv run python --version)"
echo "Starting server..."
uv run python main.py "$@"
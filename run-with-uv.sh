#!/bin/bash
# Script to run the atlasvibe server with uv-managed Python 3.11

# Ensure we're in the project directory
cd "$(dirname "$0")"

# Create and use Python 3.11 environment
if [ ! -d ".venv-electron" ]; then
    echo "Creating Python 3.11 environment..."
    uv venv .venv-electron --python 3.11
fi

# Install dependencies
echo "Installing dependencies..."
uv pip install -r requirements.txt --python .venv-electron/bin/python

# Install Poetry in the environment
uv pip install poetry --python .venv-electron/bin/python

# Set environment variables
export PATH=".venv-electron/bin:$PATH"
export VIRTUAL_ENV="$(pwd)/.venv-electron"
export PY_INTERPRETER="$(pwd)/.venv-electron/bin/python"
export POETRY_PATH="$(pwd)/.venv-electron/bin/poetry"

# Run the server
echo "Starting atlasvibe server with Python 3.11..."
uv run --python .venv-electron/bin/python python main.py "$@"
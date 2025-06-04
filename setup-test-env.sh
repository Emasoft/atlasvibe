#!/bin/bash
# Setup script for running Playwright tests with proper Python environment

echo "Setting up test environment..."

# Ensure we're in the project directory
cd "$(dirname "$0")"

# Create Python 3.11 environment if it doesn't exist
if [ ! -d ".venv-electron" ]; then
    echo "Creating Python 3.11 environment..."
    uv venv .venv-electron --python 3.11
fi

# Install dependencies
echo "Installing Python dependencies..."
uv pip install -r requirements.txt --python .venv-electron/bin/python
uv pip install poetry --python .venv-electron/bin/python

# Create config directory
mkdir -p ~/.atlasvibe
if [ ! -f ~/.atlasvibe/atlasvibe.yaml ]; then
    echo "LOG_LEVEL: INFO" > ~/.atlasvibe/atlasvibe.yaml
fi

# Create a Python interpreter cache file for the Electron app
APP_DATA_DIR=~/Library/Application\ Support
mkdir -p "$APP_DATA_DIR"
echo "$(pwd)/.venv-electron/bin/python" > "$APP_DATA_DIR/atlasvibe_py_interpreter"

# Set environment variables
export PATH="$(pwd)/.venv-electron/bin:$PATH"
export VIRTUAL_ENV="$(pwd)/.venv-electron"
export PY_INTERPRETER="$(pwd)/.venv-electron/bin/python"
export POETRY_PATH="$(pwd)/.venv-electron/bin/poetry"
export UV_PYTHON_PREFERENCE=only-managed

echo "Test environment setup complete!"
echo "Python interpreter: $(which python)"
echo "Python version: $(python --version)"
echo "Poetry path: $(which poetry)"

# Run the tests if provided as argument
if [ "$1" ]; then
    echo "Running tests: $@"
    npx playwright test "$@"
fi
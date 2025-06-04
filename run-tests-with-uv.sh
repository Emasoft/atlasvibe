#!/bin/bash
# Script to run Playwright tests with uv-managed Python 3.11 environment

echo "Setting up test environment with uv..."

# Ensure we're in the project directory
cd "$(dirname "$0")"

# Pin Python version to 3.11 if not already done
if [ ! -f ".python-version" ] || [ "$(cat .python-version)" != "3.11" ]; then
    echo "Pinning Python version to 3.11..."
    uv python pin 3.11
fi

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating Python 3.11 virtual environment..."
    uv venv
fi

# Sync dependencies
echo "Syncing dependencies..."
uv sync

# Install Poetry (needed by Electron app)
echo "Installing Poetry..."
uv pip install poetry

# Create config directory
mkdir -p ~/.atlasvibe
if [ ! -f ~/.atlasvibe/atlasvibe.yaml ]; then
    echo "LOG_LEVEL: INFO" > ~/.atlasvibe/atlasvibe.yaml
fi

# Update Python interpreter cache for Electron app
echo "$(pwd)/.venv/bin/python" > "$HOME/Library/Application Support/atlasvibe_py_interpreter"

# Display environment info
echo "Test environment ready!"
echo "Python version: $(uv run python --version)"
echo "Python path: $(uv run which python)"
echo "Poetry path: $(uv run which poetry)"

# Run the tests if provided as argument
if [ "$1" ]; then
    echo "Running tests: $@"
    npx playwright test "$@"
fi
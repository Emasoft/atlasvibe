#!/bin/bash
# Script to run tests with uv-managed Python environment

set -e  # Exit on error

echo "Setting up test environment..."

# Ensure we're in the project directory
cd "$(dirname "$0")"

# Verify Python version is pinned
if [ ! -f ".python-version" ] || [ "$(cat .python-version)" != "3.11" ]; then
    echo "Pinning Python version to 3.11..."
    uv python pin 3.11
fi

# Ensure virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment with Python 3.11..."
    uv venv --python 3.11
    echo "Syncing dependencies..."
    uv sync --all-extras
    echo "Installing Poetry..."
    uv pip install poetry
fi

# Ensure configuration exists
mkdir -p ~/.atlasvibe
if [ ! -f ~/.atlasvibe/atlasvibe.yaml ]; then
    echo "LOG_LEVEL: INFO" > ~/.atlasvibe/atlasvibe.yaml
fi

# Update Python interpreter cache
echo "$(pwd)/.venv/bin/python" > "$HOME/Library/Application Support/atlasvibe_py_interpreter"

# Display environment info
echo "Environment ready:"
echo "  Python: $(uv run python --version)"
echo "  Location: $(uv run which python)"
echo "  Poetry: $(uv run which poetry 2>/dev/null || echo 'Not installed')"

# Run the command passed as arguments
if [ "$#" -gt 0 ]; then
    echo "Running: $@"
    "$@"
else
    echo "No command specified. Usage: $0 <command>"
    echo "Example: $0 npx playwright test --headed"
fi
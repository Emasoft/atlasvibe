#!/bin/bash
# Script to run AtlasVibe server directly with uv (no Electron)

set -e

echo "Setting up AtlasVibe server environment with uv..."

# Ensure we're in the project directory
cd "$(dirname "$0")"
PROJECT_DIR=$(pwd)

# 1. Setup Python environment
if [ ! -f ".python-version" ] || [ "$(cat .python-version)" != "3.11" ]; then
    echo "Setting Python version to 3.11..."
    uv python pin 3.11
fi

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    uv venv --python 3.11
fi

# 2. Sync dependencies
echo "Installing/updating dependencies..."
uv sync --all-extras

# 3. Install atlasvibe package if needed
if ! uv pip show atlasvibe >/dev/null 2>&1; then
    echo "Installing atlasvibe package..."
    cd pkgs/atlasvibe && uv pip install -e . && cd ../..
fi

# 4. Setup environment variables
export VIRTUAL_ENV="$PROJECT_DIR/.venv"
export PYTHONPATH="$PROJECT_DIR:$PROJECT_DIR/pkgs:$PROJECT_DIR/pkgs/atlasvibe:$PROJECT_DIR/pkgs/atlasvibe_sdk:$PYTHONPATH"
export UV_PYTHON="$VIRTUAL_ENV/bin/python"

# 4. Display environment info
echo ""
echo "Environment setup complete:"
echo "  Python: $(uv run python --version)"
echo "  Python path: $(uv run which python)"
echo "  PYTHONPATH: $PYTHONPATH"
echo ""

# 5. Start the server
echo "Starting AtlasVibe server on http://localhost:5392..."
echo "Press Ctrl+C to stop the server"
echo ""

# Run the server with uv
uv run python main.py "$@"
#!/bin/bash
# Script to run AtlasVibe with uv-managed Python environment
# This ensures the app uses the correct Python 3.11 runtime

set -e

# Ensure we're in the project directory
cd "$(dirname "$0")"
PROJECT_DIR=$(pwd)

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Error: Virtual environment not found. Run ./build-and-test.sh first."
    exit 1
fi

# Setup environment variables
export VIRTUAL_ENV="$PROJECT_DIR/.venv"
export PYTHONPATH="$PROJECT_DIR:$PROJECT_DIR/pkgs/atlasvibe:$PROJECT_DIR/pkgs/atlasvibe_sdk:$PYTHONPATH"
export UV_PYTHON="$VIRTUAL_ENV/bin/python"
export PATH="$VIRTUAL_ENV/bin:$PATH"

# Update Python interpreter cache
echo "$UV_PYTHON" > "$HOME/Library/Application Support/atlasvibe_py_interpreter"

# Check what we're running
if [ "$1" == "server" ]; then
    # Run the server directly
    echo "Starting AtlasVibe server with uv..."
    echo "Python: $(uv run python --version)"
    echo "Python path: $(uv run which python)"
    shift  # Remove 'server' from arguments
    exec uv run python main.py "$@"
elif [ "$1" == "app" ]; then
    # Run the Electron app
    shift  # Remove 'app' from arguments
    APP_PATH="dist/mac-universal/atlasvibe.app/Contents/MacOS/atlasvibe"
    if [ ! -f "$APP_PATH" ]; then
        APP_PATH="dist/mac-universal-arm64-temp/atlasvibe.app/Contents/MacOS/atlasvibe"
    fi
    if [ ! -f "$APP_PATH" ]; then
        echo "Error: Electron app not found. Run ./build-and-test.sh --electron first."
        exit 1
    fi
    echo "Starting AtlasVibe app..."
    exec "$APP_PATH" "$@"
else
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  server       Run the AtlasVibe server directly"
    echo "  app          Run the Electron app"
    echo ""
    echo "Options:"
    echo "  --log-level debug    Set log level (for server)"
    echo ""
    echo "Examples:"
    echo "  $0 server                    # Run server with default settings"
    echo "  $0 server --log-level debug  # Run server with debug logging"
    echo "  $0 app                       # Run Electron app"
    exit 1
fi
#!/bin/bash
# Script to set up Python 3.11 for the packaged Electron app

set -e

echo "Setting up Python 3.11 for packaged app..."

# Get the uv Python 3.11 path
UV_PYTHON_PATH=""

# Check common uv Python locations
if [ -f "$HOME/.local/share/uv/python/cpython-3.11.12-macos-aarch64-none/bin/python3" ]; then
    UV_PYTHON_PATH="$HOME/.local/share/uv/python/cpython-3.11.12-macos-aarch64-none/bin/python3"
elif [ -f "$HOME/.local/share/uv/python/cpython-3.11.12-macos-x86_64-none/bin/python3" ]; then
    UV_PYTHON_PATH="$HOME/.local/share/uv/python/cpython-3.11.12-macos-x86_64-none/bin/python3"
elif command -v python3.11 &> /dev/null; then
    UV_PYTHON_PATH=$(which python3.11)
else
    echo "Error: Python 3.11 not found. Please install it with: uv python install 3.11"
    exit 1
fi

echo "Found Python 3.11 at: $UV_PYTHON_PATH"

# Update the Python interpreter cache
CACHE_DIR="$HOME/Library/Application Support"
mkdir -p "$CACHE_DIR"
echo "$UV_PYTHON_PATH" > "$CACHE_DIR/atlasvibe_py_interpreter"
echo "Updated Python interpreter cache"

# Create a symlink to python3.11 if it doesn't exist
if ! command -v python3.11 &> /dev/null; then
    echo "Creating python3.11 symlink..."
    sudo ln -sf "$UV_PYTHON_PATH" /usr/local/bin/python3.11
    echo "Created symlink: /usr/local/bin/python3.11 -> $UV_PYTHON_PATH"
fi

# Verify the setup
echo ""
echo "Verification:"
echo "Python 3.11 location: $(which python3.11 2>/dev/null || echo 'Not found in PATH')"
echo "Python version: $(python3.11 --version 2>/dev/null || echo 'Unable to get version')"
echo "Cached interpreter: $(cat "$CACHE_DIR/atlasvibe_py_interpreter" 2>/dev/null || echo 'No cache')"

echo ""
echo "Setup complete! The packaged app should now find Python 3.11."
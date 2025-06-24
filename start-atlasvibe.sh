#!/bin/bash

# AtlasVibe Portable Launcher for Linux/macOS
# This script starts AtlasVibe from any location

echo ""
echo "============================================"
echo "  AtlasVibe Portable - Visual Programming IDE"
echo "============================================"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Set the app directory relative to script location
APP_DIR="$SCRIPT_DIR/AtlasVibe-Portable"

# Determine the executable name based on platform
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    ELECTRON_EXE="$APP_DIR/atlasvibe.app/Contents/MacOS/atlasvibe"
else
    # Linux
    ELECTRON_EXE="$APP_DIR/atlasvibe"
fi

# Check if the executable exists
if [ ! -f "$ELECTRON_EXE" ] && [ ! -d "$APP_DIR/atlasvibe.app" ]; then
    echo "ERROR: AtlasVibe executable not found at:"
    echo "  $ELECTRON_EXE"
    echo ""
    echo "Please ensure the AtlasVibe-Portable folder is in the same directory as this script."
    exit 1
fi

# Set environment variables for portable operation
export PORTABLE_EXECUTABLE_DIR="$APP_DIR"
export NODE_ENV=production

# Use local paths for config
export XDG_CONFIG_HOME="$APP_DIR/config"
export XDG_DATA_HOME="$APP_DIR/data"
export XDG_CACHE_HOME="$APP_DIR/cache"

# Create necessary directories if they don't exist
mkdir -p "$XDG_CONFIG_HOME" "$XDG_DATA_HOME" "$XDG_CACHE_HOME"

# Add Python to PATH if it exists in resources
if [ -d "$APP_DIR/resources/PYTHON" ]; then
    export PATH="$APP_DIR/resources/PYTHON:$APP_DIR/resources/PYTHON/bin:$PATH"
fi

# Log startup information
echo "Starting AtlasVibe from: $APP_DIR"
echo "Working directory: $(pwd)"
echo ""

# Start AtlasVibe
echo "Launching AtlasVibe..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS - use open command
    open "$APP_DIR/atlasvibe.app" --args "$@"
else
    # Linux - run directly
    cd "$APP_DIR"
    "$ELECTRON_EXE" "$@" &
    cd - > /dev/null
fi

echo ""
echo "AtlasVibe started successfully!"

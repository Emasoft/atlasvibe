#!/bin/bash
# Installation script for AtlasVibe
# This script builds and installs AtlasVibe as a Python package

set -e

echo "==============================================="
echo "AtlasVibe Installation Script"
echo "==============================================="

# Check Python version
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
if [[ ! "$PYTHON_VERSION" =~ ^3\.(11|12)$ ]]; then
    echo "Error: Python 3.11 or 3.12 is required. Found: $PYTHON_VERSION"
    exit 1
fi

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "Error: Node.js is required but not found."
    echo "Please install Node.js from https://nodejs.org/"
    exit 1
fi

# Check if pnpm is installed
if ! command -v pnpm &> /dev/null; then
    echo "Installing pnpm..."
    npm install -g pnpm
fi

# Install Python dependencies
echo ""
echo "Installing Python dependencies..."
uv pip install -r requirements.txt

# Install Node.js dependencies
echo ""
echo "Installing Node.js dependencies..."
pnpm install

# Build the frontend
echo ""
echo "Building frontend..."
pnpm run build

# Build the Python package
echo ""
echo "Building Python package..."
uv pip install build
uv run python -m build

# Install the package
echo ""
echo "Installing AtlasVibe..."
uv pip install dist/*.whl

echo ""
echo "==============================================="
echo "AtlasVibe installation complete!"
echo ""
echo "You can now run:"
echo "  atlasvibe           # Run the full application"
echo "  atlasvibe server    # Run only the backend server"
echo "  atlasvibe ui        # Run only the UI"
echo "  atlasvibe init PATH # Create a new project"
echo "==============================================="
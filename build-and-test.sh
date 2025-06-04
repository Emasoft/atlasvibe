#!/bin/bash
# Comprehensive build and test script for atlasvibe using uv

set -e  # Exit on error

echo "======================================"
echo "AtlasVibe Build and Test Setup"
echo "======================================"

# Ensure we're in the project directory
cd "$(dirname "$0")"

# 1. Install Python versions if needed
echo "Step 1: Installing Python versions..."
uv python install 3.11 3.12

# 2. Pin Python version to 3.11 for this project
echo "Step 2: Pinning Python version to 3.11..."
uv python pin 3.11

# 3. Create virtual environment with Python 3.11
echo "Step 3: Creating virtual environment with Python 3.11..."
rm -rf .venv
uv venv --python 3.11

# 4. Sync dependencies
echo "Step 4: Syncing dependencies..."
uv sync --all-extras

# 5. Install Poetry (needed by Electron app)
echo "Step 5: Installing Poetry in the environment..."
uv pip install poetry

# 6. Create necessary directories and config
echo "Step 6: Setting up configuration..."
mkdir -p ~/.atlasvibe
if [ ! -f ~/.atlasvibe/atlasvibe.yaml ]; then
    echo "LOG_LEVEL: INFO" > ~/.atlasvibe/atlasvibe.yaml
fi

# 7. Update Python interpreter cache for Electron app
echo "Step 7: Updating Python interpreter cache..."
INTERPRETER_PATH="$(pwd)/.venv/bin/python"
echo "$INTERPRETER_PATH" > "$HOME/Library/Application Support/atlasvibe_py_interpreter"

# 8. Verify Python version
echo "Step 8: Verifying Python version..."
echo "Python location: $(uv run which python)"
echo "Python version: $(uv run python --version)"
echo "Poetry location: $(uv run which poetry)"

# 9. Install Node.js dependencies if not already installed
if [ ! -d "node_modules" ]; then
    echo "Step 9: Installing Node.js dependencies..."
    pnpm install
else
    echo "Step 9: Node.js dependencies already installed"
fi

# 10. Build the frontend
echo "Step 10: Building frontend..."
pnpm run build

# 11. Package the Electron app for current platform
echo "Step 11: Packaging Electron app..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    pnpm run electron-package:mac
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    pnpm run electron-package:linux
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    pnpm run electron-package:windows
fi

echo "======================================"
echo "Build complete!"
echo "======================================"

# Run tests if requested
if [ "$1" == "--test" ]; then
    echo "Running tests..."
    shift  # Remove --test from arguments
    if [ "$#" -gt 0 ]; then
        npx playwright test "$@"
    else
        npx playwright test
    fi
elif [ "$1" == "--test-headed" ]; then
    echo "Running tests with UI..."
    shift  # Remove --test-headed from arguments
    if [ "$#" -gt 0 ]; then
        npx playwright test --headed "$@"
    else
        npx playwright test --headed
    fi
fi
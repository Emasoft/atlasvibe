#!/bin/bash
# Script to run Playwright tests with proper Python environment

set -e

echo "Setting up Python environment for tests..."

# Ensure we're in the project directory
cd "$(dirname "$0")"

# 1. Set up uv environment
if [ ! -f ".python-version" ] || [ "$(cat .python-version)" != "3.11" ]; then
    echo "Setting Python version to 3.11..."
    uv python pin 3.11
fi

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    uv venv --python 3.11
    uv sync --all-extras
    uv pip install poetry
fi

# 2. Get Python path
PYTHON_PATH=$(uv run which python)
echo "Python path: $PYTHON_PATH"

# 3. Update Python interpreter cache
CACHE_DIR="$HOME/Library/Application Support"
mkdir -p "$CACHE_DIR"
echo "$PYTHON_PATH" > "$CACHE_DIR/atlasvibe_py_interpreter"

# 4. Create symlink to python3.11 if needed
if ! command -v python3.11 &> /dev/null; then
    UV_PYTHON="/Users/emanuelesabetta/.local/share/uv/python/cpython-3.11.12-macos-aarch64-none/bin/python3"
    if [ -f "$UV_PYTHON" ]; then
        echo "Creating python3.11 symlink..."
        sudo ln -sf "$UV_PYTHON" /usr/local/bin/python3.11 2>/dev/null || true
    fi
fi

# 5. Set environment variables for the packaged app
export PY_INTERPRETER="$PYTHON_PATH"
export PYTHONPATH="$(pwd):$(pwd)/pkgs/atlasvibe:$(pwd)/pkgs/atlasvibe_sdk"
export PATH="/usr/local/bin:$PATH"

# 6. Install Poetry in the app's expected location
PIPX_HOME="$HOME/.local/pipx"
if [ ! -d "$PIPX_HOME/venvs/poetry" ]; then
    echo "Installing Poetry via pipx..."
    uv run python -m pip install --user pipx
    uv run python -m pipx install poetry --force
fi

# 7. Restore original pyproject.toml if needed
if [ -f "pyproject.toml.backup" ]; then
    echo "Restoring original pyproject.toml..."
    mv pyproject.toml.backup pyproject.toml
fi

# 8. Run tests
echo ""
echo "Running tests..."
echo "Command: npx playwright test $@"
npx playwright test "$@"
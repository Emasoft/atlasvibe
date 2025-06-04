#!/bin/bash
# Script to set up Python environment for Electron app build

set -e

echo "Setting up Python environment for build..."

# Ensure we're in the project directory
cd "$(dirname "$0")"

# 1. Ensure Python 3.11 is installed and pinned
echo "Ensuring Python 3.11 is installed..."
uv python install 3.11
uv python pin 3.11

# 2. Create a fresh virtual environment
echo "Creating virtual environment..."
rm -rf .venv
uv venv --python 3.11

# 3. Sync all dependencies
echo "Installing dependencies..."
uv sync --all-extras

# 4. Install Poetry in the venv (required by Electron app)
echo "Installing Poetry..."
uv pip install poetry

# 5. Set up Python interpreter cache for Electron
echo "Setting up Python interpreter cache..."
INTERPRETER_PATH="$(pwd)/.venv/bin/python"
CACHE_DIR="$HOME/Library/Application Support"
mkdir -p "$CACHE_DIR"
echo "$INTERPRETER_PATH" > "$CACHE_DIR/atlasvibe_py_interpreter"

# 6. Create a wrapper script that the Electron app can use
echo "Creating Python wrapper script..."
cat > python-wrapper.sh << 'EOF'
#!/bin/bash
# Wrapper script to ensure Python 3.11 is used

# Try to find Python 3.11 in various locations
if command -v python3.11 &> /dev/null; then
    exec python3.11 "$@"
elif [ -f "$HOME/.local/share/uv/python/cpython-3.11.12-macos-aarch64-none/bin/python3" ]; then
    exec "$HOME/.local/share/uv/python/cpython-3.11.12-macos-aarch64-none/bin/python3" "$@"
elif [ -f "$HOME/.local/share/uv/python/cpython-3.11.12-macos-x86_64-none/bin/python3" ]; then
    exec "$HOME/.local/share/uv/python/cpython-3.11.12-macos-x86_64-none/bin/python3" "$@"
elif [ -f ".venv/bin/python" ]; then
    exec ".venv/bin/python" "$@"
else
    echo "Error: Python 3.11 not found" >&2
    exit 1
fi
EOF

chmod +x python-wrapper.sh

# 7. Verify the setup
echo "Verifying Python setup..."
echo "Python version: $(uv run python --version)"
echo "Python location: $(uv run which python)"
echo "Poetry available: $(uv run poetry --version 2>/dev/null || echo 'Not found')"

echo "Setup complete!"
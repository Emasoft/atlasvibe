#!/bin/bash
# Script to test Electron app with proper uv Python 3.11 environment

set -e

echo "Creating test deployment with uv..."

# 1. Clean and create deployment directory
rm -rf temp_test
mkdir -p temp_test
cd temp_test

# 2. Create Python 3.11 venv with uv
echo "Creating Python 3.11 virtual environment..."
uv venv --python 3.11
source .venv/bin/activate

# 3. Copy the Electron app
echo "Copying Electron app..."
cp -r ../dist/mac-universal-arm64-temp/atlasvibe.app .

# 4. Copy all required Python files
echo "Copying Python files..."
cp -r ../blocks ../captain ../main.py ../PYTHON ../pkgs .
cp ../pyproject.toml ../requirements.txt ../README.md .
cp -r ../atlasvibe_engine ../cli . 2>/dev/null || true

# 5. Install Python dependencies with uv
echo "Installing Python dependencies..."
uv pip install -r requirements.txt

# 5a. Install atlasvibe package separately
echo "Installing atlasvibe package..."
cd pkgs/atlasvibe && uv pip install -e . && cd ../..

# 6. Set up Python discovery for the app
echo "Setting up Python discovery..."
PYTHON_PATH="$(pwd)/.venv/bin/python"
echo "Python path: $PYTHON_PATH"

# Update the interpreter cache
CACHE_DIR="$HOME/Library/Application Support"
mkdir -p "$CACHE_DIR"
echo "$PYTHON_PATH" > "$CACHE_DIR/atlasvibe_py_interpreter"

# 7. Create a wrapper script for the app
cat > run-app.sh << 'EOF'
#!/usr/bin/env bash
# Script to run AtlasVibe app with uv-managed Python environment
# Usage: ./run-app.sh <PROJECT_ROOT_DIR> [additional args]

# Check if PROJECT_ROOT_DIR is provided
if [ $# -lt 1 ]; then
    echo "Usage: $0 <PROJECT_ROOT_DIR> [additional args]"
    echo "Example: $0 /Users/emanuelesabetta/Code/ATLASVIBE/atlasvibe"
    exit 1
fi

PROJECT_ROOT_DIR="$1"
shift  # Remove first argument so "$@" contains only additional args

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Set up environment variables using PROJECT_ROOT_DIR
export UV_PYTHON="$PROJECT_ROOT_DIR/temp_test/.venv/bin/python"
export VIRTUAL_ENV="$PROJECT_ROOT_DIR/temp_test/.venv"
export PATH="$VIRTUAL_ENV/bin:$PATH"
export PYTHONPATH="$PROJECT_ROOT_DIR/temp_test:$PROJECT_ROOT_DIR/temp_test/pkgs/atlasvibe:$PROJECT_ROOT_DIR/temp_test/pkgs/atlasvibe_sdk:$PYTHONPATH"

# Run the app
"$SCRIPT_DIR/atlasvibe.app/Contents/MacOS/atlasvibe" "$@"
EOF
chmod +x run-app.sh

# 8. Create test runner script
cat > run-tests.sh << 'EOF'
#!/usr/bin/env bash
# Script to run Playwright tests with uv-managed Python environment
# Usage: ./run-tests.sh <PROJECT_ROOT_DIR> [test file] [additional args]

# Check if PROJECT_ROOT_DIR is provided
if [ $# -lt 1 ]; then
    echo "Usage: $0 <PROJECT_ROOT_DIR> [test file] [additional args]"
    echo "Example: $0 /Users/emanuelesabetta/Code/ATLASVIBE/atlasvibe 16_edit_custom_block_code.spec.ts --headed"
    exit 1
fi

PROJECT_ROOT_DIR="$1"
shift  # Remove first argument so "$@" contains only test args

# Set up environment variables using PROJECT_ROOT_DIR
export UV_PYTHON="$PROJECT_ROOT_DIR/temp_test/.venv/bin/python"
export VIRTUAL_ENV="$PROJECT_ROOT_DIR/temp_test/.venv"
export PATH="$VIRTUAL_ENV/bin:$PATH"
export PYTHONPATH="$PROJECT_ROOT_DIR/temp_test:$PROJECT_ROOT_DIR/temp_test/pkgs/atlasvibe:$PROJECT_ROOT_DIR/temp_test/pkgs/atlasvibe_sdk:$PYTHONPATH"

# Ensure app uses our Python
echo "$UV_PYTHON" > "$HOME/Library/Application Support/atlasvibe_py_interpreter"

# Create symlink for mac-universal in the PROJECT_ROOT_DIR
cd "$PROJECT_ROOT_DIR"
rm -rf dist/mac-universal
ln -sf mac-universal-arm64-temp dist/mac-universal

# Run tests
npx playwright test "$@"
EOF
chmod +x run-tests.sh

echo ""
echo "Deployment complete!"
echo ""
echo "To run the app:"
echo "  cd temp_test && ./run-app.sh $(pwd)"
echo ""
echo "To run tests:"
echo "  cd temp_test && ./run-tests.sh $(pwd) 16_edit_custom_block_code.spec.ts --headed"
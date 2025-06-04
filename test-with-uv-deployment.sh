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
#!/bin/bash
export UV_PYTHON="$(pwd)/.venv/bin/python"
export VIRTUAL_ENV="$(pwd)/.venv"
export PATH="$(pwd)/.venv/bin:$PATH"
export PYTHONPATH="$(pwd):$(pwd)/pkgs/atlasvibe:$(pwd)/pkgs/atlasvibe_sdk:$PYTHONPATH"

# Run the app
./atlasvibe.app/Contents/MacOS/atlasvibe "$@"
EOF
chmod +x run-app.sh

# 8. Create test runner script
cat > run-tests.sh << 'EOF'
#!/bin/bash
cd ..
export UV_PYTHON="$(pwd)/temp_test/.venv/bin/python"
export VIRTUAL_ENV="$(pwd)/temp_test/.venv"
export PATH="$(pwd)/temp_test/.venv/bin:$PATH"
export PYTHONPATH="$(pwd)/temp_test:$(pwd)/temp_test/pkgs/atlasvibe:$(pwd)/temp_test/pkgs/atlasvibe_sdk:$PYTHONPATH"

# Ensure app uses our Python
echo "$UV_PYTHON" > "$HOME/Library/Application Support/atlasvibe_py_interpreter"

# Create symlink for mac-universal
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
echo "  cd temp_test && ./run-app.sh"
echo ""
echo "To run tests:"
echo "  cd temp_test && ./run-tests.sh 16_edit_custom_block_code.spec.ts --headed"
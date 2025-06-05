#!/bin/bash
# Comprehensive build and test script for atlasvibe using uv

set -e  # Exit on error

echo "======================================"
echo "AtlasVibe Build and Test Setup"
echo "======================================"

# Ensure we're in the project directory
cd "$(dirname "$0")"
PROJECT_DIR=$(pwd)

# Parse arguments
BUILD_ELECTRON=false
RUN_PYTHON_TESTS=false
RUN_E2E_TESTS=false
E2E_HEADED=false

for arg in "$@"; do
    case $arg in
        --electron)
            BUILD_ELECTRON=true
            ;;
        --python-tests)
            RUN_PYTHON_TESTS=true
            ;;
        --e2e-tests)
            RUN_E2E_TESTS=true
            ;;
        --headed)
            E2E_HEADED=true
            ;;
        --all-tests)
            RUN_PYTHON_TESTS=true
            RUN_E2E_TESTS=true
            ;;
        *)
            echo "Unknown argument: $arg"
            echo "Usage: $0 [--electron] [--python-tests] [--e2e-tests] [--headed] [--all-tests]"
            exit 1
            ;;
    esac
done

# 1. Install Python versions if needed
echo "Step 1: Checking Python versions..."
if ! uv python list --only-installed | grep -q "3.11"; then
    echo "Installing Python 3.11..."
    uv python install 3.11
fi

# 2. Pin Python version to 3.11 for this project
echo "Step 2: Pinning Python version to 3.11..."
uv python pin 3.11

# 3. Create virtual environment with Python 3.11 if needed
if [ ! -d ".venv" ]; then
    echo "Step 3: Creating virtual environment with Python 3.11..."
    uv venv --python 3.11
else
    echo "Step 3: Virtual environment already exists"
fi

# 4. Sync dependencies
echo "Step 4: Syncing Python dependencies..."
uv sync --all-extras

# 5. Install atlasvibe package in development mode
echo "Step 5: Installing atlasvibe package..."
cd pkgs/atlasvibe && uv pip install -e . && cd ../..

# 6. Create necessary directories and config
echo "Step 6: Setting up configuration..."
mkdir -p ~/.atlasvibe
if [ ! -f ~/.atlasvibe/atlasvibe.yaml ]; then
    echo "LOG_LEVEL: INFO" > ~/.atlasvibe/atlasvibe.yaml
fi

# 7. Update Python interpreter cache for Electron app
echo "Step 7: Updating Python interpreter cache..."
INTERPRETER_PATH="$PROJECT_DIR/.venv/bin/python"
echo "$INTERPRETER_PATH" > "$HOME/Library/Application Support/atlasvibe_py_interpreter"

# 8. Verify Python version
echo "Step 8: Verifying Python version..."
echo "Python location: $(uv run which python)"
echo "Python version: $(uv run python --version)"

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

# 11. Package the Electron app if requested
if [ "$BUILD_ELECTRON" = true ]; then
    echo "Step 11: Packaging Electron app..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        pnpm run electron-package:mac
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        pnpm run electron-package:linux
    elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
        pnpm run electron-package:windows
    fi
fi

echo "======================================"
echo "Build complete!"
echo "======================================"

# Setup environment for tests
export VIRTUAL_ENV="$PROJECT_DIR/.venv"
export PYTHONPATH="$PROJECT_DIR:$PROJECT_DIR/pkgs/atlasvibe:$PROJECT_DIR/pkgs/atlasvibe_sdk:$PYTHONPATH"
export UV_PYTHON="$VIRTUAL_ENV/bin/python"

# Run Python tests if requested
if [ "$RUN_PYTHON_TESTS" = true ]; then
    echo ""
    echo "Running Python tests..."
    uv run pytest tests/ -v || PYTHON_TESTS_FAILED=1
fi

# Run E2E tests if requested
if [ "$RUN_E2E_TESTS" = true ]; then
    echo ""
    echo "Running E2E tests..."
    if [ "$E2E_HEADED" = true ]; then
        ./run-tests-with-uv.sh --headed || E2E_TESTS_FAILED=1
    else
        ./run-tests-with-uv.sh || E2E_TESTS_FAILED=1
    fi
fi

# Summary
if [ "$RUN_PYTHON_TESTS" = true ] || [ "$RUN_E2E_TESTS" = true ]; then
    echo ""
    echo "Test Summary"
    echo "============"
    if [ "$RUN_PYTHON_TESTS" = true ]; then
        if [ -z "$PYTHON_TESTS_FAILED" ]; then
            echo "✅ Python tests: PASSED"
        else
            echo "❌ Python tests: FAILED"
        fi
    fi
    if [ "$RUN_E2E_TESTS" = true ]; then
        if [ -z "$E2E_TESTS_FAILED" ]; then
            echo "✅ E2E tests: PASSED"
        else
            echo "❌ E2E tests: FAILED"
        fi
    fi
    
    if [ -n "$PYTHON_TESTS_FAILED" ] || [ -n "$E2E_TESTS_FAILED" ]; then
        exit 1
    fi
fi

echo ""
echo "All operations completed successfully!"
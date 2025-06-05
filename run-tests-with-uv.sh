#!/bin/bash
# Script to run Playwright tests with uv-managed backend server
# This bypasses Electron packaging issues by running the server directly

set -e

echo "Setting up test environment with uv..."

# Ensure we're in the project directory
cd "$(dirname "$0")"
PROJECT_DIR=$(pwd)

# 1. Setup Python environment
if [ ! -f ".python-version" ] || [ "$(cat .python-version)" != "3.11" ]; then
    echo "Setting Python version to 3.11..."
    uv python pin 3.11
fi

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment with Python 3.11..."
    uv venv --python 3.11
fi

# 2. Sync dependencies
echo "Installing/updating Python dependencies..."
uv sync --all-extras

# 3. Install atlasvibe package in development mode
echo "Installing atlasvibe package..."
cd pkgs/atlasvibe && uv pip install -e . && cd ../..

# 4. Setup environment variables
export VIRTUAL_ENV="$PROJECT_DIR/.venv"
export PYTHONPATH="$PROJECT_DIR:$PROJECT_DIR/pkgs/atlasvibe:$PROJECT_DIR/pkgs/atlasvibe_sdk:$PYTHONPATH"
export UV_PYTHON="$VIRTUAL_ENV/bin/python"

# 5. Kill any existing server on port 5392
echo "Checking for existing server on port 5392..."
if lsof -i :5392 >/dev/null 2>&1; then
    echo "Killing existing server..."
    kill $(lsof -t -i :5392) 2>/dev/null || true
    sleep 2
fi

# 6. Start the backend server in background
echo "Starting AtlasVibe backend server..."
uv run python main.py --log-level debug > server.log 2>&1 &
SERVER_PID=$!

# Wait for server to be ready
echo "Waiting for server to start..."
for i in {1..30}; do
    if curl -s http://localhost:5392/health >/dev/null 2>&1; then
        echo "Server is ready!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "Server failed to start. Check server.log for details."
        cat server.log
        kill $SERVER_PID 2>/dev/null || true
        exit 1
    fi
    sleep 1
done

# 7. Build the frontend if needed
if [ ! -d "dist" ] || [ "$1" == "--build" ]; then
    echo "Building frontend..."
    pnpm run build
fi

# 8. Run Playwright tests
echo "Running Playwright tests..."

# Function to cleanup on exit
cleanup() {
    echo "Cleaning up..."
    kill $SERVER_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
}
trap cleanup EXIT

# Determine which tests to run
if [ -n "$1" ] && [ "$1" != "--build" ]; then
    # Specific test file provided
    TEST_FILE="$1"
    shift
else
    # Run the block editing test by default
    TEST_FILE="playwright-test/16_edit_custom_block_code.spec.ts"
fi

# Check if we should run in headed mode
if [ "$1" == "--headed" ] || [ "$2" == "--headed" ]; then
    PLAYWRIGHT_ARGS="--headed"
else
    PLAYWRIGHT_ARGS=""
fi

# Set environment for Playwright to connect to our server
export VITE_API_URL="http://localhost:5392"
export PLAYWRIGHT_BASE_URL="http://localhost:3000"

# Start frontend dev server for Playwright tests
echo "Starting frontend dev server..."
pnpm run dev > frontend.log 2>&1 &
FRONTEND_PID=$!

# Wait for frontend to be ready
echo "Waiting for frontend to start..."
for i in {1..30}; do
    if curl -s http://localhost:3000 >/dev/null 2>&1; then
        echo "Frontend is ready!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "Frontend failed to start. Check frontend.log for details."
        cat frontend.log
        cleanup
        exit 1
    fi
    sleep 1
done

# Run the tests
echo "Running test: $TEST_FILE"
npx playwright test "$TEST_FILE" $PLAYWRIGHT_ARGS "${@:2}"

# Capture test exit code
TEST_EXIT_CODE=$?

# Show server logs if tests failed
if [ $TEST_EXIT_CODE -ne 0 ]; then
    echo ""
    echo "Tests failed. Server logs:"
    echo "========================"
    tail -n 50 server.log
fi

exit $TEST_EXIT_CODE
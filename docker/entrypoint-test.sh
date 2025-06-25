#!/bin/bash
set -euo pipefail

echo "=== AtlasVibe Docker Test Environment ==="
echo "Starting headless test environment with uv..."
echo "Python: $(python --version)"
echo "uv: $(uv --version)"

# Function to cleanup on exit
cleanup() {
    echo "Cleaning up..."
    if [ ! -z "${XVFB_PID:-}" ]; then
        kill $XVFB_PID 2>/dev/null || true
    fi
    if [ ! -z "${SERVER_PID:-}" ]; then
        kill $SERVER_PID 2>/dev/null || true
    fi
}
trap cleanup EXIT

# Create config directory if it doesn't exist
mkdir -p ~/.atlasvibe
if [ ! -f ~/.atlasvibe/atlasvibe.yaml ]; then
    echo "docker: true" > ~/.atlasvibe/atlasvibe.yaml
fi

# Start Xvfb (virtual display) - this prevents any window from opening on host
echo "Starting Xvfb virtual display..."
Xvfb :99 -screen 0 ${XVFB_SCREEN_SIZE:-1280x1024x24} -ac -nolisten tcp -nolisten unix &
XVFB_PID=$!

# Wait for Xvfb to be ready
sleep 2

# Verify Xvfb is running
if ! ps -p $XVFB_PID > /dev/null; then
    echo "ERROR: Xvfb failed to start!"
    exit 1
fi

echo "Virtual display started successfully (PID: $XVFB_PID)"

# Export display for all child processes
export DISPLAY=:99

# Additional Electron settings for headless mode
export ELECTRON_DISABLE_GPU=1
export ELECTRON_NO_SANDBOX=1
export ELECTRON_ENABLE_LOGGING=1

# Start the application services using uv
echo "Starting AtlasVibe services with uv..."
uv run pnpm run start-project:ci &
SERVER_PID=$!

# Wait for services to be ready
echo "Waiting for services to be ready..."
for i in {1..30}; do
    if curl -s http://localhost:5392/log_level > /dev/null 2>&1; then
        echo "Backend is ready!"
        break
    fi
    echo -n "."
    sleep 1
done
echo ""

# Verify services are running
if ! ps -p $SERVER_PID > /dev/null; then
    echo "ERROR: Services failed to start!"
    exit 1
fi

# Run the tests with uv
echo "Running Playwright tests with uv..."
uv run python /app/run_tests_docker.py
TEST_EXIT_CODE=$?

echo "Tests completed with exit code: $TEST_EXIT_CODE"
exit $TEST_EXIT_CODE

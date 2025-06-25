#!/bin/sh
# Docker test entrypoint script for AtlasVibe

# Start Xvfb in background with proper settings
Xvfb :99 -screen 0 1280x1024x24 -ac -nolisten tcp -nolisten unix > /dev/null 2>&1 &
XVFB_PID=$!
sleep 3

# Verify Xvfb is running
if ! ps -p $XVFB_PID > /dev/null; then
  echo 'ERROR: Xvfb failed to start'
  exit 1
fi

echo 'Virtual display started successfully'

echo 'Starting backend and frontend services...'
uv run pnpm run start-project:ci &
SERVER_PID=$!

echo 'Waiting for services to be ready...'
sleep 30

echo 'Running tests...'
uv run python /app/run_tests_docker.py
TEST_EXIT_CODE=$?

# Cleanup
kill $SERVER_PID || true
kill $XVFB_PID || true

exit $TEST_EXIT_CODE

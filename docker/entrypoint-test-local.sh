#!/bin/sh
# Docker test entrypoint for LOCAL profile
# Runs comprehensive tests with higher timeouts and retries

echo "🏠 Starting AtlasVibe LOCAL Test Environment"
echo "Profile: LOCAL (Development)"
echo "Max retries: ${MAX_RETRIES:-10}"
echo "Timeout multiplier: ${TIMEOUT_MULTIPLIER:-2}x"
echo "Skip slow tests: ${SKIP_SLOW_TESTS:-false}"
echo "=========================================="

# Start Xvfb
Xvfb :99 -screen 0 1280x1024x24 -ac -nolisten tcp -nolisten unix > /dev/null 2>&1 &
XVFB_PID=$!
sleep 3

if ! ps -p $XVFB_PID > /dev/null; then
  echo '❌ ERROR: Xvfb failed to start'
  exit 1
fi

echo '✅ Virtual display started'

# Start backend
echo '🚀 Starting backend service...'
export DISABLE_FILE_WATCHER=true
export DISABLE_CHANGE_QUEUE=true
uv run python3 main.py &
BACKEND_PID=$!

# Start frontend (for local profile)
echo '🚀 Starting frontend service...'
cd /app && pnpm run dev > /app/test-logs/frontend.log 2>&1 &
FRONTEND_PID=$!

echo "Backend PID: $BACKEND_PID"
echo "Frontend PID: $FRONTEND_PID"

# Function to check if a service is ready
wait_for_service() {
  local url=$1
  local name=$2
  local max_attempts=${3:-60}
  local attempt=0

  echo "⏳ Waiting for $name at $url..."

  while [ $attempt -lt $max_attempts ]; do
    if curl -s -f "$url" > /dev/null 2>&1; then
      echo "✅ $name is ready!"
      return 0
    fi
    attempt=$((attempt + 1))
    sleep 1
  done

  echo "❌ ERROR: $name failed to start after $max_attempts seconds"
  return 1
}

# Wait for services
sleep 10  # Initial delay for services to start

if ! wait_for_service "http://localhost:5392/log_level" "Backend API" 60; then
  echo "Backend logs:"
  tail -50 /app/test-logs/backend.log || true
  kill $BACKEND_PID $FRONTEND_PID $XVFB_PID 2>/dev/null || true
  exit 1
fi

if [ "$SKIP_FRONTEND_CHECK" != "true" ]; then
  if ! wait_for_service "http://localhost:5173" "Frontend Dev Server" 60; then
    echo "Frontend logs:"
    tail -50 /app/test-logs/frontend.log || true
    kill $BACKEND_PID $FRONTEND_PID $XVFB_PID 2>/dev/null || true
    exit 1
  fi
fi

echo '✅ All services are ready!'

# Run comprehensive test suite
echo '🧪 Running LOCAL test suite...'
echo '=========================================='

# Create test results directory
mkdir -p /app/test-results

# Run Python unit tests
echo '📋 Running Python unit tests...'
uv run pytest -v \
  --tb=short \
  --junit-xml=/app/test-results/pytest-results.xml \
  --cov=. \
  --cov-report=html:/app/test-results/coverage \
  --cov-report=term \
  $([ "$SKIP_SLOW_TESTS" = "true" ] && echo "-m 'not slow'" || echo "") \
  . || TEST_FAILED=1

# Run Playwright E2E tests
echo '📋 Running Playwright E2E tests...'
export PWTEST_SKIP_TEST_OUTPUT=1
pnpm exec playwright test \
  --config=playwright.config.docker.ts \
  --reporter=json \
  --output=/app/test-results || TEST_FAILED=1

# Run integration tests if enabled
if [ "$RUN_INTEGRATION_TESTS" = "true" ]; then
  echo '📋 Running integration tests...'
  uv run python /app/run_integration_tests.py || TEST_FAILED=1
fi

# Generate test report
echo '📊 Generating test report...'
uv run python /app/run_tests_docker.py

# Cleanup
echo '🧹 Cleaning up...'
kill $BACKEND_PID $FRONTEND_PID $XVFB_PID 2>/dev/null || true

# Exit with appropriate code
if [ "$TEST_FAILED" = "1" ]; then
  echo '❌ Some tests failed!'
  exit 1
else
  echo '✅ All tests passed!'
  exit 0
fi

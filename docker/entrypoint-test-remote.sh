#!/bin/sh
# Docker test entrypoint for REMOTE profile (GitHub CI)
# Optimized for faster execution with lower timeouts

echo "☁️  Starting AtlasVibe REMOTE Test Environment"
echo "Profile: REMOTE (GitHub CI)"
echo "Max retries: ${MAX_RETRIES:-3}"
echo "Timeout multiplier: ${TIMEOUT_MULTIPLIER:-1}x"
echo "Skip slow tests: ${SKIP_SLOW_TESTS:-true}"
echo "=========================================="

# Start Xvfb
Xvfb :99 -screen 0 1280x1024x24 -ac -nolisten tcp -nolisten unix > /dev/null 2>&1 &
XVFB_PID=$!
sleep 2

if ! ps -p $XVFB_PID > /dev/null; then
  echo '::error::Xvfb failed to start'
  exit 1
fi

echo '✅ Virtual display started'

# Start backend only (skip frontend for CI)
echo '🚀 Starting backend service...'
export DISABLE_FILE_WATCHER=true
export DISABLE_CHANGE_QUEUE=true
export CI=true
export GITHUB_ACTIONS=true

uv run python3 main.py > /app/test-logs/backend.log 2>&1 &
BACKEND_PID=$!

echo "Backend PID: $BACKEND_PID"

# Function to check if a service is ready (faster for CI)
wait_for_service() {
  local url=$1
  local name=$2
  local max_attempts=${3:-30}  # Lower timeout for CI
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

  echo "::error::$name failed to start after $max_attempts seconds"
  return 1
}

# Wait for backend
sleep 5  # Shorter initial delay for CI

if ! wait_for_service "http://localhost:5392/log_level" "Backend API" 30; then
  echo "::group::Backend logs"
  tail -100 /app/test-logs/backend.log || true
  echo "::endgroup::"
  kill $BACKEND_PID $XVFB_PID 2>/dev/null || true
  exit 1
fi

echo '✅ Backend service is ready!'

# Run fast test suite for CI
echo '🧪 Running REMOTE test suite (optimized for CI)...'
echo '=========================================='

# Create test results directory
mkdir -p /app/test-results

# Run Python unit tests (skip slow tests)
echo '::group::Python unit tests'
echo '📋 Running Python unit tests (fast only)...'
uv run pytest -v \
  --tb=short \
  --junit-xml=/app/test-results/pytest-results.xml \
  -m "not slow" \
  --maxfail=10 \
  . || TEST_FAILED=1
echo '::endgroup::'

# Run minimal Playwright tests
echo '::group::Playwright E2E tests'
echo '📋 Running Playwright E2E tests (smoke tests only)...'
export PWTEST_SKIP_TEST_OUTPUT=1
pnpm exec playwright test \
  --config=playwright.config.docker.ts \
  --grep="@smoke" \
  --reporter=github \
  --reporter=json \
  --output=/app/test-results || TEST_FAILED=1
echo '::endgroup::'

# Generate test report
echo '::group::Test Report'
echo '📊 Generating test report...'
uv run python /app/run_tests_docker.py
echo '::endgroup::'

# Cleanup
echo '🧹 Cleaning up...'
kill $BACKEND_PID $XVFB_PID 2>/dev/null || true

# Create GitHub Actions summary if in CI
if [ "$GITHUB_ACTIONS" = "true" ]; then
  echo "## Test Results Summary" >> $GITHUB_STEP_SUMMARY
  echo "" >> $GITHUB_STEP_SUMMARY
  if [ -f /app/test-results/summary.md ]; then
    cat /app/test-results/summary.md >> $GITHUB_STEP_SUMMARY
  fi
fi

# Exit with appropriate code
if [ "$TEST_FAILED" = "1" ]; then
  echo '::error::Some tests failed!'
  exit 1
else
  echo '✅ All tests passed!'
  exit 0
fi

#!/bin/bash
# Docker test runner with JSON output and cleanup

set -e

echo "🐳 AtlasVibe Docker Test Runner (JSON output)"
echo "==========================================="

# Cleanup function
cleanup() {
    echo -e "\n🧹 Cleaning up Docker containers..."
    docker ps -a | grep atlasvibe | awk '{print $1}' | xargs -r docker rm -f 2>/dev/null || true
}

trap cleanup EXIT

# Ensure test results directory exists
mkdir -p test-results playwright-report

# Run test container
echo "🚀 Running tests in Docker container..."

docker run --name "atlasvibe-test-json-$(date +%s)" --rm \
  -e CI=true \
  -e NODE_ENV=test \
  -e DISPLAY=:99 \
  -e DISABLE_FILE_WATCHER=true \
  -e DISABLE_CHANGE_QUEUE=true \
  -v "$(pwd)/test-results:/app/test-results" \
  -v "$(pwd)/playwright-report:/app/playwright-report" \
  atlasvibe-test:latest \
  /bin/bash -c '
    # Start Xvfb
    Xvfb :99 -screen 0 1280x1024x24 -ac &
    XVFB_PID=$!

    # Start backend
    cd /app
    uv run python3 main.py &
    BACKEND_PID=$!

    # Wait for backend
    echo "⏳ Waiting for backend..."
    for i in {1..30}; do
        if curl -s http://localhost:5392/log_level >/dev/null 2>&1; then
            echo "✅ Backend ready!"
            break
        fi
        sleep 1
    done

    # Run Playwright tests with JSON reporter
    echo "🎭 Running Playwright backend tests..."
    pnpm exec playwright test \
      --config=playwright.config.docker.ts \
      --reporter=json \
      --reporter=list \
      00_docker_backend.spec.ts \
      > /app/test-results/results.json || true

    # Also run with list reporter for console output
    pnpm exec playwright test \
      --config=playwright.config.docker.ts \
      --reporter=list \
      00_docker_backend.spec.ts || true

    # Cleanup
    kill $BACKEND_PID $XVFB_PID 2>/dev/null || true

    echo "✨ Tests completed!"
  '

# Check results
echo -e "\n📊 Test Results:"
if [ -f test-results/results.json ]; then
    echo "✅ JSON results generated"
    echo "📁 Files in test-results:"
    ls -la test-results/

    # Try to parse and display summary
    if command -v jq >/dev/null 2>&1; then
        echo -e "\n📈 Test Summary:"
        jq -r '.stats | "Total: \(.total), Passed: \(.passed), Failed: \(.failed), Skipped: \(.skipped)"' test-results/results.json 2>/dev/null || echo "Could not parse JSON"
    fi
else
    echo "⚠️  No JSON results file generated"
fi

echo -e "\n✅ Docker test completed and cleaned up!"

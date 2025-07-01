#!/bin/bash
# Simple Docker test runner for AtlasVibe

echo "🐳 Building AtlasVibe test Docker image..."
docker build -f Dockerfile.test -t atlasvibe-test:latest . || {
    echo "❌ Docker build failed"
    exit 1
}

echo "✅ Docker image built successfully"
echo "🚀 Running tests in Docker container..."

# Create directories for test results
mkdir -p test-results playwright-report

# Run the container
docker run --rm \
  -e DISPLAY=:99 \
  -e CI=true \
  -e NODE_ENV=test \
  -e ELECTRON_DISABLE_GPU=1 \
  -e ELECTRON_NO_SANDBOX=1 \
  -e XVFB_SCREEN_SIZE=1280x1024x24 \
  -v "$(pwd)/test-results:/app/test-results" \
  -v "$(pwd)/playwright-report:/app/playwright-report" \
  atlasvibe-test:latest

exit_code=$?

echo ""
echo "📊 Test Results:"
echo "================"
if [ -f test-results/results.json ]; then
    echo "✅ Test results generated"
    ls -la test-results/
else
    echo "⚠️  No test results file found"
fi

if [ $exit_code -eq 0 ]; then
    echo "🎉 Tests passed!"
else
    echo "❌ Tests failed with exit code: $exit_code"
fi

exit $exit_code

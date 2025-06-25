#!/bin/bash
# Quick Docker test runner that skips build if image exists

echo "🐳 AtlasVibe Docker Test Runner (Quick Mode)"
echo "=========================================="
echo ""

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Check if image exists
if docker images | grep -q "atlasvibe-atlasvibe-test"; then
    echo "✅ Docker image already exists, skipping build"
else
    echo "🔧 Building Docker test image..."
    docker-compose build atlasvibe-test || exit 1
fi

# Remove any existing display variable
unset DISPLAY

echo ""
echo "🧪 Running tests in Docker container..."
echo ""

# Run tests
docker-compose run \
    --rm \
    --no-deps \
    -e DISPLAY=:99 \
    -e ELECTRON_DISABLE_GPU=1 \
    -e ELECTRON_NO_SANDBOX=1 \
    -e XVFB_SCREEN_SIZE=1280x1024x24 \
    atlasvibe-test

TEST_EXIT_CODE=$?

echo ""
echo "🧹 Cleaning up..."
docker-compose down

echo ""
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "✅ Tests completed successfully!"
else
    echo "❌ Tests failed with exit code: $TEST_EXIT_CODE"
fi

exit $TEST_EXIT_CODE

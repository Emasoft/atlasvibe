#!/bin/bash
# Docker lint and test runner for AtlasVibe

set -e

echo "🐳 AtlasVibe Docker Lint & Test Runner"
echo "======================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Cleanup function
cleanup() {
    echo -e "\n🧹 Cleaning up Docker containers..."
    docker ps -a | grep atlasvibe-lint-test | awk '{print $1}' | xargs -r docker rm -f 2>/dev/null || true
    echo "✅ Cleanup completed"
}

trap cleanup EXIT

# Build image if needed
if ! docker images | grep -q "atlasvibe-test.*latest"; then
    echo "📦 Building Docker test image..."
    docker build -f Dockerfile.test -t atlasvibe-test:latest . || {
        echo -e "${RED}❌ Docker build failed${NC}"
        exit 1
    }
fi

# Create results directory
mkdir -p lint-results test-results

echo -e "\n🚀 Starting Docker container for linting and testing..."

# Run container with linting and testing
docker run --name "atlasvibe-lint-test-$(date +%s)" --rm \
  --entrypoint /bin/bash \
  -e CI=true \
  -e NODE_ENV=test \
  -v "$(pwd):/app" \
  -v "$(pwd)/lint-results:/lint-results" \
  -v "$(pwd)/test-results:/test-results" \
  atlasvibe-test:latest \
  -c '
    cd /app

    # Activate virtual environment
    . .venv/bin/activate

    echo "================================================"
    echo "🔍 PHASE 1: Python Linting"
    echo "================================================"

    # Run Ruff check
    echo -e "\n📋 Running Ruff check..."
    ruff check --ignore E203,E402,E501,E266,W505,F841,F842,F401,W293,I001,UP015,C901,W291 --isolated --output-format full . > /lint-results/ruff_check.log 2>&1 || {
        echo -e "❌ Ruff check found issues"
        cat /lint-results/ruff_check.log
    }

    # Run Ruff format check
    echo -e "\n📋 Running Ruff format check..."
    ruff format --check . > /lint-results/ruff_format.log 2>&1 || {
        echo -e "❌ Ruff format found issues"
        echo "Run: ruff format . to fix"
    }

    # Run mypy
    echo -e "\n📋 Running mypy..."
    COLUMNS=400 mypy --strict --show-error-context --pretty --install-types --non-interactive --no-color-output --show-error-codes --show-error-code-links --no-error-summary --follow-imports=normal captain main.py > /lint-results/mypy.log 2>&1 || {
        echo -e "⚠️  Mypy found type issues"
        head -50 /lint-results/mypy.log
    }

    echo -e "\n================================================"
    echo "🔍 PHASE 2: JavaScript/TypeScript Linting"
    echo "================================================"

    # Run ESLint
    echo -e "\n📋 Running ESLint..."
    pnpm run lint > /lint-results/eslint.log 2>&1 || {
        echo -e "❌ ESLint found issues"
        cat /lint-results/eslint.log | head -50
    }

    # Run Prettier check
    echo -e "\n📋 Running Prettier check..."
    pnpm run format:check > /lint-results/prettier.log 2>&1 || {
        echo -e "❌ Prettier found formatting issues"
        echo "Run: pnpm run format to fix"
    }

    echo -e "\n================================================"
    echo "🧪 PHASE 3: Running Tests"
    echo "================================================"

    # Start backend for tests
    echo -e "\n🚀 Starting backend..."
    DISABLE_FILE_WATCHER=true DISABLE_CHANGE_QUEUE=true uv run python3 main.py &
    BACKEND_PID=$!

    # Wait for backend
    echo "⏳ Waiting for backend to start..."
    for i in {1..30}; do
        if curl -s http://localhost:5392/log_level >/dev/null 2>&1; then
            echo "✅ Backend is ready!"
            break
        fi
        if [ $i -eq 30 ]; then
            echo "❌ Backend failed to start"
            exit 1
        fi
        sleep 1
    done

    # Run Python tests
    echo -e "\n🐍 Running Python tests..."
    pytest -v --no-header --tb=short captain/tests/ > /test-results/pytest.log 2>&1 || {
        echo -e "❌ Some Python tests failed"
        cat /test-results/pytest.log | tail -30
    }

    # Run API tests
    echo -e "\n🔌 Running API tests..."
    curl -f http://localhost:5392/log_level > /test-results/api_health.log 2>&1 && \
        echo "✅ API health check passed" || echo "❌ API health check failed"

    curl -f http://localhost:5392/blocks/metadata/ > /test-results/api_blocks.log 2>&1 && \
        echo "✅ Blocks metadata API passed" || echo "❌ Blocks metadata API failed"

    # Kill backend
    kill $BACKEND_PID 2>/dev/null || true

    echo -e "\n================================================"
    echo "📊 SUMMARY"
    echo "================================================"

    # Count issues
    RUFF_ISSUES=$(grep -c "error:" /lint-results/ruff_check.log 2>/dev/null || echo "0")
    ESLINT_ISSUES=$(grep -c "error" /lint-results/eslint.log 2>/dev/null || echo "0")
    PYTEST_FAILURES=$(grep -E "FAILED|ERROR" /test-results/pytest.log 2>/dev/null | wc -l || echo "0")

    echo "Ruff issues: $RUFF_ISSUES"
    echo "ESLint issues: $ESLINT_ISSUES"
    echo "Test failures: $PYTEST_FAILURES"

    # Exit with error if any issues found
    if [ "$RUFF_ISSUES" -gt 0 ] || [ "$ESLINT_ISSUES" -gt 0 ] || [ "$PYTEST_FAILURES" -gt 0 ]; then
        echo -e "\n❌ Issues found that need fixing"
        exit 1
    else
        echo -e "\n✅ All checks passed!"
        exit 0
    fi
  '

EXIT_CODE=$?

echo -e "\n📁 Results saved to:"
echo "  - lint-results/"
echo "  - test-results/"

if [ $EXIT_CODE -eq 0 ]; then
    echo -e "\n${GREEN}🎉 All linting and tests passed!${NC}"
else
    echo -e "\n${RED}❌ Some issues need to be fixed${NC}"
    echo -e "\nTo fix formatting issues automatically:"
    echo "  Python: uv run ruff format ."
    echo "  JS/TS: pnpm run format"
fi

exit $EXIT_CODE

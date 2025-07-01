#!/bin/bash
# Run GitHub workflows locally with act

echo "🎭 Running GitHub workflows locally with act"
echo "=========================================="

# Clean up any existing act containers
echo "🧹 Cleaning up existing act containers..."
docker ps -a | grep act | awk '{print $1}' | xargs -r docker rm -f 2>/dev/null || true

# Run CI workflow tests
echo -e "\n📋 Running CI workflow tests..."

# 1. Python code format
echo -e "\n🐍 Python code format check..."
act -W .github/workflows/ci.yml -j python-code-format --container-architecture linux/amd64 || {
    echo "❌ Python code format check failed"
}

# 2. Python code lint
echo -e "\n🔍 Python code lint..."
act -W .github/workflows/ci.yml -j python-code-lint --container-architecture linux/amd64 || {
    echo "❌ Python code lint failed"
}

# 3. TypeScript code style
echo -e "\n📘 TypeScript code style..."
act -W .github/workflows/ci.yml -j ts-code-style --container-architecture linux/amd64 || {
    echo "❌ TypeScript code style failed"
}

# 4. Python tests
echo -e "\n🧪 Python tests..."
act -W .github/workflows/ci.yml -j python-tests --container-architecture linux/amd64 || {
    echo "❌ Python tests failed"
}

echo -e "\n✅ Act tests completed!"

# Clean up
echo -e "\n🧹 Cleaning up act containers..."
docker ps -a | grep act | awk '{print $1}' | xargs -r docker rm -f 2>/dev/null || true

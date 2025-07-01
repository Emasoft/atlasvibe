#!/bin/bash
# Run CI workflow checks with act

echo "🎭 Running CI workflow checks with act"
echo "====================================="

# Clean up existing containers
docker ps -a | grep -E "(act|atlasvibe)" | awk '{print $1}' | xargs -r docker rm -f 2>/dev/null || true

# Run python format check
echo -e "\n🐍 Running Python format check..."
act -W .github/workflows/ci.yml -j python-code-format --container-architecture linux/amd64 -P ubuntu-latest=catthehacker/ubuntu:act-latest || {
    echo "❌ Python format check failed"
    exit 1
}

echo -e "\n✅ CI checks passed locally!"

# Clean up
docker ps -a | grep act | awk '{print $1}' | xargs -r docker rm -f 2>/dev/null || true

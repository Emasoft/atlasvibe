#!/bin/bash
# Simple Docker test for AtlasVibe backend

echo "🐳 Running AtlasVibe Docker Backend Test"
echo "========================================="

# Run a simple backend test
docker run --rm \
  -e DISABLE_FILE_WATCHER=true \
  -e DISABLE_CHANGE_QUEUE=true \
  atlasvibe-test:latest \
  /bin/bash -c '
    echo "Starting backend..."
    cd /app
    uv run python3 main.py &
    BACKEND_PID=$!

    echo "Waiting for backend to start..."
    sleep 10

    echo "Testing backend health endpoint..."
    curl -f http://localhost:5392/log_level && echo -e "\n✅ Backend is healthy!" || echo -e "\n❌ Backend health check failed"

    echo "Testing blocks metadata endpoint..."
    curl -f http://localhost:5392/blocks/metadata/ | head -c 200 && echo -e "\n✅ Blocks metadata endpoint works!" || echo -e "\n❌ Blocks metadata failed"

    echo "Stopping backend..."
    kill $BACKEND_PID

    echo -e "\n🎉 Docker test completed!"
  '

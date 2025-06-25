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
uv run pnpm run start-project:docker &
SERVER_PID=$!

# Give services time to start
echo 'Waiting 10 seconds for services to initialize...'
sleep 10

# Check if the process is still running
if ! ps -p $SERVER_PID > /dev/null; then
  echo 'ERROR: Server process died during startup'
  exit 1
fi

# Check what's listening on ports
echo 'Checking listening ports...'
netstat -tulpn | grep -E ':(5392|5173)' || echo 'No ports found with netstat'
ss -tulpn | grep -E ':(5392|5173)' || echo 'No ports found with ss'

# Function to check if a service is ready
wait_for_service() {
  local url=$1
  local name=$2
  local max_attempts=60  # 60 seconds timeout
  local attempt=0

  echo "Waiting for $name to be ready at $url..."

  while [ $attempt -lt $max_attempts ]; do
    # Extract port from URL (e.g., http://localhost:5392/log_level -> 5392)
    local port=$(echo "$url" | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')

    # Try Python first to check if port is open
    if python3 -c "import socket; s=socket.socket(); result=s.connect_ex(('localhost', $port)); s.close(); exit(0 if result==0 else 1)" 2>/dev/null; then
      echo "Attempt $attempt: Port is open, trying HTTP request..."
      # Port is open, try curl
      response=$(curl -s -w "\n%{http_code}" "$url" 2>&1 || echo "CURL_FAILED")
      http_code=$(echo "$response" | tail -n1)

      if [ "$response" = "CURL_FAILED" ]; then
        echo "Attempt $attempt: curl failed despite port being open"
      else
        echo "Attempt $attempt: HTTP $http_code from $url"
        # Check if status code starts with 2, 3, or 4
        case "$http_code" in
          2*|3*|4*)
            echo "$name is ready!"
            return 0
            ;;
        esac
      fi
    else
      echo "Attempt $attempt: Port $port is not open yet"
    fi

    attempt=$((attempt + 1))
    sleep 1
  done

  echo "ERROR: $name failed to start after $max_attempts seconds"
  return 1
}

# Wait for backend to be ready (AtlasVibe backend runs on port 5392)
if ! wait_for_service "http://localhost:5392/log_level" "Backend API"; then
  echo "Backend failed to start on port 5392"
  kill $SERVER_PID || true
  kill $XVFB_PID || true
  exit 1
fi

# Wait for frontend to be ready
if ! wait_for_service "http://localhost:5173" "Frontend"; then
  echo "Frontend failed to start"
  kill $SERVER_PID || true
  kill $XVFB_PID || true
  exit 1
fi

echo 'All services are ready!'
echo 'Running tests...'
uv run python /app/run_tests_docker.py
TEST_EXIT_CODE=$?

# Cleanup
kill $SERVER_PID || true
kill $XVFB_PID || true

exit $TEST_EXIT_CODE

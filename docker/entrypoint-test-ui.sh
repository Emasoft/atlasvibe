#!/bin/sh
# Docker test entrypoint for UI testing profile
# Focuses on Electron app UI testing with Playwright

echo "🖥️  Starting AtlasVibe UI Test Environment"
echo "Profile: UI Testing (Headless Electron)"
echo "=========================================="

# Start Xvfb with higher resolution for UI testing
Xvfb :99 -screen 0 1920x1080x24 -ac -nolisten tcp -nolisten unix > /dev/null 2>&1 &
XVFB_PID=$!
sleep 3

if ! ps -p $XVFB_PID > /dev/null; then
  echo '❌ ERROR: Xvfb failed to start'
  exit 1
fi

echo '✅ Virtual display started (1920x1080)'

# Set display environment
export DISPLAY=:99
export ELECTRON_ENABLE_LOGGING=1

# Start backend service
echo '🚀 Starting backend service...'
export DISABLE_FILE_WATCHER=true
export DISABLE_CHANGE_QUEUE=true
uv run python3 main.py > /app/test-logs/backend.log 2>&1 &
BACKEND_PID=$!

# Start frontend in development mode
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
sleep 10  # Initial delay

if ! wait_for_service "http://localhost:5392/log_level" "Backend API" 60; then
  echo "Backend logs:"
  tail -50 /app/test-logs/backend.log || true
  kill $BACKEND_PID $FRONTEND_PID $XVFB_PID 2>/dev/null || true
  exit 1
fi

if ! wait_for_service "http://localhost:5173" "Frontend Dev Server" 60; then
  echo "Frontend logs:"
  tail -50 /app/test-logs/frontend.log || true
  kill $BACKEND_PID $FRONTEND_PID $XVFB_PID 2>/dev/null || true
  exit 1
fi

echo '✅ All services are ready!'

# Build the Electron app for testing
echo '📦 Building Electron app...'
pnpm run build
BUILD_STATUS=$?

if [ $BUILD_STATUS -ne 0 ]; then
  echo "❌ Build failed!"
  kill $BACKEND_PID $FRONTEND_PID $XVFB_PID 2>/dev/null || true
  exit 1
fi

echo '✅ Electron app built successfully'

# Package the Electron app
echo '📦 Packaging Electron app...'
# Use linux packaging since we're in Docker
pnpm run electron-package:linux
PACKAGE_STATUS=$?

if [ $PACKAGE_STATUS -ne 0 ]; then
  echo "❌ Packaging failed!"
  kill $BACKEND_PID $FRONTEND_PID $XVFB_PID 2>/dev/null || true
  exit 1
fi

echo '✅ Electron app packaged successfully'

# Run UI-focused Playwright tests
echo '🧪 Running UI test suite...'
echo '=========================================='

# Create test results directory
mkdir -p /app/test-results/ui

# Set Playwright to use the packaged app
export PLAYWRIGHT_ELECTRON_APP_PATH="/app/release/linux-unpacked/atlasvibe"

# Run comprehensive UI tests
echo '📋 Running Electron UI tests...'
pnpm exec playwright test \
  --config=playwright.config.docker.electron.ts \
  --reporter=json \
  --reporter=html:/app/test-results/ui/html-report \
  --output=/app/test-results/ui \
  playwright-test/ui-docker-tests.spec.ts || TEST_FAILED=1

# Run screenshot tests
echo '📸 Running screenshot comparison tests...'
pnpm exec playwright test \
  --config=playwright.config.docker.electron.ts \
  --grep="@screenshot" \
  --update-snapshots \
  --output=/app/test-results/ui/screenshots || SCREENSHOT_FAILED=1

# Run accessibility tests
echo '♿ Running accessibility tests...'
pnpm exec playwright test \
  --config=playwright.config.docker.electron.ts \
  --grep="@a11y" \
  --output=/app/test-results/ui/accessibility || A11Y_FAILED=1

# Generate comprehensive UI test report
echo '📊 Generating UI test report...'
if [ -f /app/run_ui_tests_report.py ]; then
  uv run python /app/run_ui_tests_report.py
else
  echo "⚠️  UI test report script not found, skipping report generation"
fi

# Capture final screenshots of key pages
echo '📸 Capturing UI screenshots...'
mkdir -p /app/test-results/ui/final-screenshots

# Use Playwright to capture screenshots
cat > /app/capture_screenshots.js << 'EOF'
const { _electron: electron } = require('playwright');

(async () => {
  const app = await electron.launch({
    args: ['/app/release/linux-unpacked/atlasvibe'],
    env: {
      ...process.env,
      NODE_ENV: 'production',
      DISPLAY: ':99',
      ELECTRON_DISABLE_GPU: '1',
      ELECTRON_NO_SANDBOX: '1'
    }
  });

  try {
    const window = await app.firstWindow();

    // Wait for app to fully load
    await window.waitForTimeout(5000);

    // Capture main window
    await window.screenshot({
      path: '/app/test-results/ui/final-screenshots/main-window.png',
      fullPage: true
    });

    // Navigate to flow chart if possible
    const flowChartButton = await window.$('button:has-text("Flow Chart")');
    if (flowChartButton) {
      await flowChartButton.click();
      await window.waitForTimeout(2000);
      await window.screenshot({
        path: '/app/test-results/ui/final-screenshots/flow-chart.png',
        fullPage: true
      });
    }

    console.log('✅ Screenshots captured successfully');
  } catch (error) {
    console.error('❌ Screenshot capture failed:', error);
  } finally {
    await app.close();
  }
})();
EOF

node /app/capture_screenshots.js || echo "⚠️  Screenshot capture completed with warnings"

# Cleanup
echo '🧹 Cleaning up...'
kill $BACKEND_PID $FRONTEND_PID $XVFB_PID 2>/dev/null || true

# Generate summary
echo ""
echo "=========================================="
echo "📊 UI TEST SUMMARY"
echo "=========================================="

if [ -f /app/test-results/ui/results.json ]; then
  # Parse and display results
  jq -r '.suites[].specs[].tests[] | "\(.status): \(.title)"' /app/test-results/ui/results.json || true
fi

# Exit with appropriate code
if [ "$TEST_FAILED" = "1" ] || [ "$SCREENSHOT_FAILED" = "1" ] || [ "$A11Y_FAILED" = "1" ]; then
  echo '❌ Some UI tests failed!'
  exit 1
else
  echo '✅ All UI tests passed!'
  exit 0
fi

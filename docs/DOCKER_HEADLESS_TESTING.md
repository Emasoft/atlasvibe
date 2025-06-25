# Docker Headless Testing Setup for AtlasVibe

This document explains how AtlasVibe's Docker testing environment is configured to run completely headless without attempting to open any windows on the host machine's display.

## Key Features

1. **Complete Display Isolation**: Tests run in a virtual display (Xvfb) inside the container
2. **No Host Display Connection**: Container cannot access host's display server
3. **Automatic Browser Installation**: Playwright browsers are installed inside the container
4. **Formatted Test Results**: Beautiful table output showing test results

## Architecture

### Docker Configuration

The Dockerfile includes a dedicated test stage with:

- All required X11 and GTK dependencies for headless Electron
- Playwright base image with browser support
- Xvfb (X Virtual Framebuffer) for virtual display
- Environment variables to force headless operation

### Key Environment Variables

```bash
DISPLAY=:99                  # Virtual display number
CI=true                      # Indicates CI environment
NODE_ENV=test               # Test environment
ELECTRON_DISABLE_GPU=1      # Disable GPU acceleration
ELECTRON_NO_SANDBOX=1       # Disable sandbox (required in Docker)
```

### Security Measures

1. **Xvfb Configuration**: Started with `-nolisten tcp -nolisten unix` to prevent network connections
2. **Docker Security**: `no-new-privileges:true` prevents privilege escalation
3. **Display Isolation**: Host DISPLAY variable is unset before running container

## Usage

### Quick Start

```bash
# Run all tests in Docker (completely headless)
npm run docker:test

# Or using the script directly
./test-docker.sh
```

### Manual Docker Commands

```bash
# Build the test container
docker-compose build atlasvibe-test

# Run tests
docker-compose run --rm atlasvibe-test

# Run with custom environment
docker-compose run --rm -e DISPLAY=:99 atlasvibe-test
```

## File Structure

```
docker/
├── entrypoint-test.sh      # Test environment setup script
├── Dockerfile              # Multi-stage build with test stage
└── docker-compose.yml      # Service definitions

playwright-test/
├── 00_headless_check.spec.ts  # Verifies headless operation
├── 00_api_smoke.spec.ts       # API connectivity tests
└── 00_docker_smoke.spec.ts    # Docker-specific tests

run_tests_docker.py         # Test runner with formatted output
playwright.config.docker.ts # Docker-specific Playwright config
test-docker.sh             # Convenience script
```

## How It Works

1. **Container Startup**:

   - Xvfb starts on display :99 with 1280x1024x24 resolution
   - Virtual display is verified before proceeding
   - No TCP/Unix listeners to prevent external connections

2. **Service Launch**:

   - Backend (FastAPI) starts on port 5392
   - Frontend (if needed) starts on port 5173
   - Services run inside container network

3. **Test Execution**:

   - Playwright runs with headless Chrome
   - Tests interact with virtual display
   - Screenshots/videos saved to mounted volumes

4. **Results Display**:
   - Python script parses JSON test results
   - Formats output in beautiful table
   - Shows pass/fail/skip with emojis

## Troubleshooting

### Tests Still Opening Windows on Host?

1. Ensure DISPLAY is unset: `unset DISPLAY`
2. Check Docker daemon is running
3. Verify no X11 forwarding in SSH: `ssh -x`

### Container Can't Start Xvfb?

1. Check Docker has enough resources
2. Ensure all X11 dependencies installed
3. Try different display number if :99 is taken

### Tests Failing to Connect?

1. Services may need more startup time
2. Check correct ports (5392 for backend)
3. Verify network connectivity inside container

## Example Output

```
🐳 AtlasVibe Docker Test Runner
================================

🔧 Building Docker images...
✅ Docker images built successfully

🧪 Running tests in Docker container...

🚀 Starting AtlasVibe Docker Tests...
⏰ Start time: 2025-06-25 09:45:38
================================================================================

📋 Running Playwright tests...

================================================================================
📊 TEST RESULTS SUMMARY
================================================================================
Total Tests: 3
✅ Passed: 3
❌ Failed: 0
⏭️  Skipped: 0
⏱️  Duration: 15.23s
================================================================================

📋 DETAILED TEST RESULTS
========================================================================================================================
Status     Suite                     Test Name                                Description                         Duration
========================================================================================================================
✅ PASSED  Headless Docker Envir..   Verify running in headless mode          Verify running in headless mode     0.123s
✅ PASSED  Headless Docker Envir..   Backend API responds in Docker           Backend api responds in docker      0.456s
✅ PASSED  Headless Docker Envir..   Can take screenshot without opening d..  Can take screenshot without opening 0.789s
========================================================================================================================

🎉 ALL TESTS PASSED! 🎉
```

## Benefits

1. **Consistent Testing**: Same environment locally and in CI
2. **No Display Issues**: Works on headless servers
3. **Resource Efficient**: No GPU required
4. **Secure**: Isolated from host system
5. **Portable**: Runs anywhere Docker runs

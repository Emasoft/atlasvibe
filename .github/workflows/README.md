# GitHub Workflows for AtlasVibe

## Docker Headless Testing Workflows

This directory contains GitHub Actions workflows that run headless tests in Docker containers with identical configurations to local development.

### Workflows

1. **docker-headless-test.yml** - Basic Docker headless test runner
   - Runs on push/PR to main
   - Uses Dockerfile.test for quick testing
   - Uploads test results as artifacts

2. **docker-compose-test.yml** - Docker Compose based testing
   - Uses docker-compose.yml for orchestration
   - Better for complex multi-service tests
   - Includes Docker logs on failure

3. **docker-matrix-test.yml** - Multi-platform testing
   - Tests on linux/amd64 and linux/arm64
   - Uses QEMU for cross-platform builds
   - Generates combined test report

4. **docker-quick-test.yml** - Manual quick test runner
   - Workflow dispatch with custom test patterns
   - Debug mode support
   - Minimal 15-minute timeout

5. **docker-e2e-test.yml** - Full E2E testing in Docker
   - Runs complete Playwright E2E suite
   - Captures screenshots on failure
   - Comments results on PRs

### Key Features

- **Complete Headless Operation**: All workflows ensure no display connection to host
- **Xvfb Virtual Display**: Uses display :99 with proper isolation flags
- **Identical Configuration**: Same environment variables as local testing
- **Artifact Collection**: Test results, reports, and screenshots uploaded
- **PR Integration**: Automatic comments with test summaries

### Environment Variables

All Docker test workflows use these standard variables:
```yaml
DISPLAY: :99
CI: true
NODE_ENV: test
ELECTRON_DISABLE_GPU: 1
ELECTRON_NO_SANDBOX: 1
XVFB_SCREEN_SIZE: 1280x1024x24
```

### Usage

The workflows are triggered automatically on:
- Push to main branch
- Pull requests to main branch
- Manual workflow dispatch

### Debugging

To debug failing tests:
1. Check the uploaded artifacts for test results and screenshots
2. Use the docker-quick-test.yml workflow with debug mode enabled
3. Review Docker logs in the workflow output

### Local Testing

To run the same tests locally:
```bash
# Using Docker Compose
npm run docker:test

# Using minimal Dockerfile
docker build -f Dockerfile.test -t atlasvibe-test .
docker run --rm atlasvibe-test

# Quick test without rebuild
./test-docker-quick.sh
```

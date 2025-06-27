# AtlasVibe Test Automation Guide

This document describes the comprehensive test automation system for AtlasVibe that works seamlessly across local development and CI/CD environments.

## Overview

The test automation system automatically detects the environment and runs appropriate tests with optimized configurations. It supports:

- **Smart Test Detection**: Only runs tests affected by changes
- **Environment-Aware Configuration**: Different settings for local/remote/Docker
- **Parallel Execution**: Maximizes resource utilization
- **Comprehensive Reporting**: Detailed results with artifacts

## Quick Start

### Run All Tests Automatically

```bash
./run-tests-auto.sh
```

### Run Specific Test Categories

```bash
# Skip Docker tests (faster)
./run-tests-auto.sh --skip-docker

# Skip UI tests
./run-tests-auto.sh --skip-ui

# Force specific environment
./run-tests-auto.sh --env remote
```

### Run UI Tests Only

```bash
./run-ui-tests.sh
```

### Run Docker Tests

```bash
./test-docker-comprehensive.sh all
```

## Environment Detection

The system automatically detects three environments:

### 1. Local Environment

- **Detection**: Default when not in CI or Docker
- **Characteristics**:
  - Extended timeouts (2x)
  - All tests enabled
  - Parallel execution
  - Debug logging
  - 10 retries for flaky tests

### 2. Remote/CI Environment

- **Detection**: `CI=true` or `GITHUB_ACTIONS=true`
- **Characteristics**:
  - Optimized timeouts (1x)
  - Skip slow tests
  - Limited parallelism
  - Info logging
  - 3 retries for flaky tests

### 3. Docker Environment

- **Detection**: Running inside Docker container
- **Characteristics**:
  - Moderate timeouts (1.5x)
  - Headless mode
  - Virtual display (Xvfb)
  - Sequential execution
  - 5 retries for flaky tests

## Test Categories

### Python Tests

- **Unit Tests**: Individual function tests
- **Integration Tests**: Component interaction tests
- **Block Tests**: AtlasVibe block functionality
- **Backend Tests**: FastAPI endpoint tests

```bash
# Run all Python tests
uv run pytest -v .

# Run specific category
uv run pytest -v blocks/
uv run pytest -v captain/

# Run with coverage
uv run pytest --cov=. --cov-report=html
```

### JavaScript/TypeScript Tests

- **Component Tests**: React component tests
- **Utility Tests**: Helper function tests
- **Linting**: Code style checks
- **Type Checking**: TypeScript validation

```bash
# Run all JS tests
pnpm test

# Run linting
pnpm run lint

# Check formatting
pnpm run format:check
```

### Docker Container Tests

- **Local Profile**: Full test suite with frontend
- **Remote Profile**: Backend-only, optimized for CI
- **Integration Profile**: GitHub cloning, build tests
- **UI Profile**: Headless Electron app tests

```bash
# Run specific profile
./test-docker-comprehensive.sh local
./test-docker-comprehensive.sh remote
./test-docker-comprehensive.sh integration
./test-docker-comprehensive.sh ui

# Skip Docker build
./test-docker-comprehensive.sh remote --skip-build
```

### UI Tests

- **App Launch**: Electron app startup
- **Navigation**: Sidebar and routing
- **Block Operations**: Drag & drop, palette
- **Accessibility**: Keyboard navigation, ARIA
- **Performance**: Load times, memory usage

```bash
# Run locally with GUI
HEADLESS=false ./run-ui-tests.sh

# Run in Docker (headless)
./test-docker-comprehensive.sh ui

# Run specific UI test
pnpm exec playwright test playwright-test/ui-docker-tests.spec.ts
```

## Configuration Files

### Environment Configurations

Located in `test-config/`:

- `local.env`: Local development settings
- `remote.env`: CI/CD optimized settings
- `docker.env`: Container-specific settings

### Example Configuration

```env
# test-config/local.env
MAX_RETRIES=10
TIMEOUT_MULTIPLIER=2
SKIP_SLOW_TESTS=false
RUN_INTEGRATION_TESTS=true
RUN_UI_TESTS=true
PARALLEL_JOBS=4
HEADLESS=false
LOG_LEVEL=debug
```

## Smart Test Detection

The `detect-tests.py` script analyzes changed files to determine which tests to run:

```bash
# Show test plan
python detect-tests.py

# Get JSON output for automation
python detect-tests.py --json
```

### Detection Rules

- Python file changes → Python tests
- TypeScript changes → JavaScript tests + UI tests
- Docker file changes → Docker rebuild + tests
- Package file changes → Full test suite

## CI/CD Integration

### GitHub Actions Workflow

The `.github/workflows/automated-tests.yml` workflow:

1. **Detects Required Tests**: Based on changed files
2. **Runs Tests in Parallel**: Matrix strategy for speed
3. **Platform Testing**: Ubuntu, macOS, Windows
4. **Automatic Reporting**: Comments on PRs

### Manual Workflow Dispatch

```yaml
workflow_dispatch:
  inputs:
    test_profile:
      description: "Test profile to run"
      options:
        - auto # Smart detection
        - quick # Fast subset
        - full # Everything
        - ui-only # Just UI tests
```

## Pre-commit Integration

Add test hooks to `.pre-commit-config.yaml`:

```yaml
- repo: local
  hooks:
    - id: quick-tests
      name: Quick Tests
      entry: ./run-tests-auto.sh --env local --skip-docker
      language: system
      pass_filenames: false
      stages: [push]
```

## Troubleshooting

### Common Issues

#### 1. UI Tests Fail Locally

```bash
# Install system dependencies
sudo apt-get install -y libgtk-3-0 libgbm1 libnss3

# Install Playwright browsers
pnpm exec playwright install chromium
```

#### 2. Docker Tests Timeout

```bash
# Increase Docker resources
# Docker Desktop → Settings → Resources
# - CPUs: 4+
# - Memory: 8GB+

# Use skip-build flag
./test-docker-comprehensive.sh remote --skip-build
```

#### 3. Python Import Errors

```bash
# Recreate virtual environment
uv venv
uv sync --all-extras --dev
```

#### 4. Flaky Tests

```bash
# Run with increased retries
MAX_RETRIES=20 ./run-tests-auto.sh

# Run specific test with debugging
uv run pytest -xvs path/to/test.py::test_name
```

### Debug Mode

Enable detailed logging:

```bash
# Set debug environment
export LOG_LEVEL=debug
export PYTEST_VERBOSE=true
export PLAYWRIGHT_DEBUG=1

# Run with verbose output
./run-tests-auto.sh --env local
```

## Performance Tips

### 1. Parallel Execution

```bash
# Python tests
uv run pytest -n auto

# Playwright tests
pnpm exec playwright test --workers=4
```

### 2. Test Caching

```bash
# Use pytest cache
uv run pytest --lf  # Run last failed
uv run pytest --ff  # Failed first

# Docker layer caching
docker compose build --build-arg BUILDKIT_INLINE_CACHE=1
```

### 3. Selective Testing

```bash
# Only run changed tests
./detect-tests.py --json | jq -r '.test_commands[].[1]' | parallel -j4

# Skip slow tests locally
SKIP_SLOW_TESTS=true ./run-tests-auto.sh
```

## Best Practices

1. **Write Fast Tests**: Aim for <1s per test
2. **Use Fixtures**: Share expensive setup
3. **Mock External Services**: Don't depend on network
4. **Clean State**: Each test should be independent
5. **Descriptive Names**: Test names should explain intent
6. **Regular Cleanup**: Remove obsolete tests

## Monitoring Test Health

### Test Metrics

- **Coverage**: Aim for >80% coverage
- **Duration**: Track test suite runtime
- **Flakiness**: Monitor intermittent failures
- **Dependencies**: Keep test dependencies minimal

### Reporting

Test results are saved in `test-results/`:

- `summary.md`: Overall test summary
- `python/`: Python test artifacts
- `js/`: JavaScript test results
- `ui/`: UI test screenshots and reports
- `docker/`: Container test logs

## Future Enhancements

1. **Test Impact Analysis**: ML-based test selection
2. **Visual Regression Testing**: Screenshot comparisons
3. **Performance Benchmarking**: Track speed over time
4. **Distributed Testing**: Run tests across multiple machines
5. **Test Prioritization**: Run most likely to fail first

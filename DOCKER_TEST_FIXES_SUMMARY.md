# Docker Test Fixes Summary

## Date: 2025-06-26

### Issues Fixed

1. **Docker Backend Test - Incorrect Endpoint**

   - **Issue**: The test was trying to access `/blocks` which returned 404
   - **Fix**: Changed to `/blocks/metadata/` which returns 200 OK
   - **File**: `playwright-test/00_docker_backend.spec.ts`

2. **Docker E2E Test - Wrong Backend Port**

   - **Issue**: The test was trying to connect to port 11060 instead of 5392
   - **Fix**: Updated the curl command to use `http://localhost:5392/log_level`
   - **File**: `.github/workflows/docker-e2e-test.yml`

3. **Docker Smoke Test - Wrong Backend Port**

   - **Issue**: The test was using port 11060 and wrong endpoint
   - **Fix**: Updated to use port 5392 and `/log_level` endpoint
   - **File**: `playwright-test/00_docker_smoke.spec.docker.ts`

4. **test.skip() Error (Already Fixed)**
   - **Issue**: `test.skip()` with function was used outside describe block
   - **Fix**: Changed to `test.skip(true, "App not launched")`
   - **File**: `playwright-test/01_app_ci.spec.ts`

### Workflows Affected

These fixes should resolve failures in:

- Docker Headless Tests
- Docker E2E Tests
- Docker Matrix Tests
- E2E Testing (Windows)

### Key Insights

1. The backend API uses port 5392, not 11060
2. The blocks endpoint is `/blocks/metadata/` not `/blocks`
3. Health check endpoint is `/log_level` not `/health`
4. Docker tests need proper virtual display setup with Xvfb

### Next Steps

1. Monitor the GitHub Actions workflows to ensure they pass
2. The Python executable issue in Docker may still need attention if tests continue to fail
3. Consider adding more robust error handling and retry logic for flaky tests

### Commit Reference

- Commit: `fix: Fix Docker test endpoint URLs and ports`
- Fixes test.skip() error and Docker endpoint/port issues

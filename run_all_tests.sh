#!/bin/bash
# Run all tests including those normally skipped
# This sets environment variables that tests can check

echo "🚀 Running ALL tests (including normally skipped ones)..."
echo "⚠️  Make sure you have all dependencies installed!"
echo ""

# Set environment variable to force run all tests
export ATLASVIBE_FORCE_RUN_ALL_TESTS=1
export PYTEST_CURRENT_TEST=1  # Some tests might check this

# Run pytest with options to show all output and run xfail tests
uv run pytest \
    -v \
    --runxfail \
    --tb=short \
    --capture=no \
    -r fEsxXpP \
    "$@"

# -v: verbose
# --runxfail: run tests marked as xfail
# --tb=short: short traceback format
# --capture=no: don't capture output (show all prints)
# -r fEsxXpP: show all test outcomes in summary
# "$@": pass any additional arguments

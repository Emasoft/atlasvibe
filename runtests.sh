#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

echo "Running Python tests..."
poetry run python -m pytest .

echo "Running Playwright tests..."
npx playwright test

echo "All tests passed!"

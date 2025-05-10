#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

echo "Setting up Poetry virtual environment and installing dependencies..."
poetry install

echo "Running Python tests..."
poetry run python -m pytest .

echo "Running Playwright tests..."
npx playwright test

echo "All tests passed!"

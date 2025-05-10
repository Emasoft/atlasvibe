#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# Ensure the script is run from the project root (where pyproject.toml exists)
if [ ! -f "pyproject.toml" ]; then
  echo "Error: pyproject.toml not found."
  echo "Please run this script from the root directory of the Poetry project."
  exit 1
fi

echo "Setting up Poetry virtual environment and installing dependencies..."
poetry install

echo "Running Python tests..."
poetry run python -m pytest .

echo "Running Playwright tests..."
npx playwright test

echo "All tests passed!"

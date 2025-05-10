#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# Ensure the script is run from the project root (where pyproject.toml exists)
if [ ! -f "pyproject.toml" ]; then
  echo "Error: pyproject.toml not found."
  echo "Please run this script from the root directory of the project."
  exit 1
fi

echo "Setting up uv virtual environment and installing dependencies..."
uv venv --python 3.11 # Or your desired Python version
uv sync -E dev # Ensure dev dependencies (like chardet, pytest) are installed

# Add project root to PYTHONPATH to ensure atlasvibe_engine is discoverable,
# prepending it to give it higher priority.
# This might be less necessary with `uv run` but kept for robustness.
export PYTHONPATH="$(pwd)${PYTHONPATH:+":$PYTHONPATH"}"

echo "Running Python tests..."
uv run pytest .

echo "Running Playwright tests..."
# Assuming Playwright is installed as a dev dependency via npm/pnpm
# and npx is available in the environment.
# If Playwright was managed by Python, this would also use `uv run`.
npx playwright test

echo "All tests passed!"

#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

echo "Installing development tools using 'uv tool install'..."

# List of tools to install
tools=(
    "nox-uv"
    "bump-my-version"
    "ruff"
    "pyright"
    "mypy"
    "prefect"
    "coverage"
    "textract"
)

for tool in "${tools[@]}"; do
    echo "Installing ${tool}..."
    uv tool install "${tool}"
done

echo "Development tools installation complete."
echo ""
echo "To use these tools and ensure they use your project-specific configurations:"
echo "1. Activate your project's virtual environment (if not already active):"
echo "   source .venv/bin/activate"
echo "   (Then you can run tools like 'ruff .', 'mypy .', etc.)"
echo ""
echo "2. Or, run them directly using 'uv run <tool_name> -- <args>':"
echo "   Example: uv run ruff check ."
echo "   Example: uv run mypy ."
echo ""
echo "These tools will look for configuration files like 'pyproject.toml', 'ruff.toml', 'mypy.ini' in your project directory."

# To upgrade all installed tools later, you can run:
# uv tool upgrade --all

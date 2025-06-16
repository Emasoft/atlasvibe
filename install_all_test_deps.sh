#!/bin/bash
# Install all optional dependencies for running complete test suite
set -euo pipefail

echo "Installing all test dependencies..."

# Install all dependencies in one command for efficiency
uv pip install \
    pytest pytest-cov pytest-mock \
    torch torchvision transformers onnx onnxruntime \
    pyarrow fastparquet sympy scikit-learn \
    prophet \
    xlrd lxml openpyxl

echo "All test dependencies installed!"
echo "You can now run: uv run pytest"
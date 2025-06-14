#!/bin/bash
# Install all optional dependencies for running complete test suite

echo "Installing all test dependencies..."

# Core test dependencies (already in dev dependencies)
echo "Installing core dependencies..."
uv pip install pytest pytest-cov pytest-mock

# Machine Learning / Deep Learning dependencies
echo "Installing ML/DL dependencies..."
uv pip install torch torchvision transformers onnx onnxruntime

# Data processing dependencies
echo "Installing data processing dependencies..."
uv pip install pyarrow fastparquet sympy scikit-learn

# Prophet dependencies
echo "Installing Prophet dependencies..."
uv pip install prophet

# Additional dependencies that might be needed
echo "Installing additional dependencies..."
uv pip install xlrd lxml openpyxl

echo "All test dependencies installed!"
echo "You can now run: uv run pytest"
# Running All Tests Locally (No Skipping)

This guide explains how to run the complete AtlasVibe test suite locally without any tests being skipped.

## Why Tests Are Skipped

Tests are skipped in CI for these reasons:

1. **Missing optional dependencies** (PyTorch, Transformers, ONNX, etc.)
2. **Large ML/DL libraries** that would slow down CI
3. **Expected failures** (xfail) due to known upstream bugs

## Method 1: Install All Dependencies (Recommended)

First, install all optional dependencies:

```bash
# Make script executable (first time only)
chmod +x install_all_test_deps.sh

# Install all test dependencies
./install_all_test_deps.sh

# Run all tests (xfail tests will still run but may fail)
uv run pytest -v --runxfail
```

## Method 2: Force Run Script (Python)

Use the force run script that overrides skip decorators:

```bash
# Make script executable (first time only)
chmod +x force_run_all_tests.py

# Run all tests, ignoring skip decorators
uv run python force_run_all_tests.py

# With additional pytest options
uv run python force_run_all_tests.py -k "test_name" --pdb
```

**Note**: This will attempt to run tests even if dependencies are missing, which will cause ImportErrors.

## Method 3: Environment Variable (Shell Script)

Use the shell script that sets environment variables:

```bash
# Make script executable (first time only)
chmod +x run_all_tests.sh

# Run all tests
./run_all_tests.sh

# With additional pytest options
./run_all_tests.sh tests/specific_test.py -k "test_pattern"
```

## Method 4: Manual pytest Command

Run pytest with all the necessary flags:

```bash
# Run all tests including xfail
uv run pytest -v --runxfail --tb=short -r fEsxXpP

# Run with specific test file
uv run pytest -v --runxfail path/to/test.py

# Run slow tests too
uv run pytest -v --runxfail --runslow
```

## Installing Specific Dependencies

If you only want to run specific test categories:

### For PyTorch/Deep Learning Tests

```bash
uv pip install torch torchvision transformers
```

### For ONNX Tests

```bash
uv pip install onnx onnxruntime
```

### For Prophet/Time Series Tests

```bash
uv pip install prophet pyarrow
```

### For Data Processing Tests

```bash
uv pip install sympy scikit-learn xlrd openpyxl
```

## Pytest Command Options Explained

- `-v` or `--verbose`: Detailed test output
- `--runxfail`: Run tests marked as expected failures
- `--runslow`: Run tests marked as slow (custom marker)
- `--tb=short`: Short traceback format
- `-r fEsxXpP`: Show all test outcomes in summary
  - `f`: failed
  - `E`: error
  - `s`: skipped
  - `x`: xfailed
  - `X`: xpassed
  - `p`: passed
  - `P`: passed with output
- `--capture=no` or `-s`: Don't capture stdout/stderr

## Checking What Will Be Skipped

To see which tests would be skipped and why:

```bash
# Show skip reasons without running tests
uv run pytest --collect-only -q | grep SKIP

# Show detailed skip information
uv run pytest -v --tb=no | grep -E "SKIPPED.*reason"
```

## Troubleshooting

1. **ImportError when forcing tests**: Install the missing dependency
2. **Tests still being skipped**: Check if tests have hardcoded version checks
3. **XFail tests failing**: This is expected - they're known issues

## CI vs Local Testing

- **CI**: Runs only core tests (fast, no optional deps)
- **Local**: Can run all tests (complete coverage)

Always ensure CI tests pass before pushing, even if you run all tests locally!

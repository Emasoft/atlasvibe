#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

echo "Starting Test Execution Script..."
echo "--------------------------------------------------"
echo "STEP 1: Setting up Python environment..."
if command -v poetry &> /dev/null
then
    echo "Poetry found. Installing Python dependencies..."
    poetry install --with dev
else
    echo "Poetry could not be found. Please install Poetry and ensure it's in your PATH."
    exit 1
fi
echo "Python environment setup complete."
echo "--------------------------------------------------"

echo "STEP 2: Setting up Node.js environment..."
if command -v npm &> /dev/null
then
    echo "npm found. Installing Node.js dependencies..."
    npm install
    # Building the Electron app using "npm run build" from package.json
    echo "Attempting to build the application (if applicable for Playwright)..."
    if npm run build; then
        echo "Application build successful."
    else
        echo "Application build failed. Continuing, but Playwright tests might not run correctly."
        # Depending on your setup, a failed build might mean Playwright tests cannot run correctly.
        # You might want to exit 1 here if a build is strictly required.
    fi
else
    echo "npm could not be found. Please install Node.js and npm."
    exit 1
fi
echo "Node.js environment setup complete."
echo "--------------------------------------------------"

# Variables to store results
pytest_status="SKIPPED"
pytest_summary="Not run"
playwright_status="SKIPPED"
playwright_summary="Not run"
overall_failure=0

# Function to run pytest
run_pytest() {
    echo "STEP 3: Running Python (pytest) tests..."
    # Run pytest and capture output.
    # We use a temporary file to capture pytest output for summary extraction.
    local pytest_output_file
    pytest_output_file=$(mktemp)
    
    # Run pytest, tee output to file and stdout, handle exit code separately
    if poetry run pytest 2>&1 | tee "$pytest_output_file"; then
        pytest_status="PASSED"
        # Try to grab a summary line, e.g., "X passed in Ys"
        pytest_summary=$(grep -E '[0-9]+ passed( in [0-9\.]+s)?' "$pytest_output_file" | tail -n 1)
        if [ -z "$pytest_summary" ]; then
            pytest_summary="All tests passed."
        fi
    else
        pytest_status="FAILED"
        overall_failure=1
        # Try to grab a summary line, e.g., "X failed, Y passed"
        pytest_summary=$(grep -E '([0-9]+ failed)?(, )?([0-9]+ passed)?' "$pytest_output_file" | tail -n 1)
        if [ -z "$pytest_summary" ]; then
            pytest_summary="One or more tests failed."
        fi
    fi
    rm "$pytest_output_file"
    echo "Python tests complete."
    echo "--------------------------------------------------"
}

# Function to run Playwright tests
run_playwright() {
    echo "STEP 4: Running Playwright (TypeScript) tests..."
    # Run Playwright tests and capture output.
    local playwright_output_file
    playwright_output_file=$(mktemp)

    if npx playwright test 2>&1 | tee "$playwright_output_file"; then
        playwright_status="PASSED"
        playwright_summary=$(grep -E '[0-9]+ tests passed' "$playwright_output_file" | tail -n 1)
         if [ -z "$playwright_summary" ]; then
            playwright_summary="All tests passed."
        fi
    else
        playwright_status="FAILED"
        overall_failure=1
        playwright_summary=$(grep -E '([0-9]+ failed)?(, )?([0-9]+ passed)?' "$playwright_output_file" | tail -n 1)
        if [ -z "$playwright_summary" ]; then
            playwright_summary="One or more tests failed."
        fi
    fi
    rm "$playwright_output_file"
    echo "Playwright tests complete."
    echo "--------------------------------------------------"
}

# Run the tests
run_pytest
run_playwright

# Print summary table
echo "STEP 5: Test Results Summary"
echo ""
printf "+------------------+----------+----------------------------------------------------+\n"
printf "| Test Suite       | Status   | Summary                                            |\n"
printf "+------------------+----------+----------------------------------------------------+\n"
printf "| Python (pytest)  | %-8s | %-50s |\n" "$pytest_status" "$pytest_summary"
printf "| Playwright       | %-8s | %-50s |\n" "$playwright_status" "$playwright_summary"
printf "+------------------+----------+----------------------------------------------------+\n"
echo ""

if [ $overall_failure -ne 0 ]; then
    echo "Overall Result: SOME TESTS FAILED"
    exit 1
else
    echo "Overall Result: ALL TESTS PASSED"
    exit 0
fi

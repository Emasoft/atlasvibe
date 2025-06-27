#!/bin/bash
# Universal UI test runner - works in local and Docker environments

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Detect environment
if [ -f /.dockerenv ]; then
    echo -e "${BLUE}🐳 Running in Docker environment${NC}"
    ENVIRONMENT="docker"
    export DISPLAY=:99
    export ELECTRON_DISABLE_GPU=1
    export ELECTRON_NO_SANDBOX=1
else
    echo -e "${GREEN}💻 Running in local environment${NC}"
    ENVIRONMENT="local"
fi

# Function to start virtual display (Docker only)
start_virtual_display() {
    if [ "$ENVIRONMENT" = "docker" ]; then
        echo -e "${BLUE}Starting virtual display...${NC}"
        Xvfb :99 -screen 0 1920x1080x24 -ac -nolisten tcp -nolisten unix &
        XVFB_PID=$!
        sleep 3

        if ! ps -p $XVFB_PID > /dev/null; then
            echo -e "${RED}Failed to start Xvfb${NC}"
            exit 1
        fi
        echo -e "${GREEN}✅ Virtual display started${NC}"
    fi
}

# Function to check if app is built
check_app_built() {
    local app_path=""

    if [ -f release/linux-unpacked/atlasvibe ]; then
        app_path="release/linux-unpacked/atlasvibe"
    elif [ -f release/mac/AtlasVibe.app/Contents/MacOS/AtlasVibe ]; then
        app_path="release/mac/AtlasVibe.app/Contents/MacOS/AtlasVibe"
    elif [ -f release/win-unpacked/AtlasVibe.exe ]; then
        app_path="release/win-unpacked/AtlasVibe.exe"
    fi

    if [ -z "$app_path" ]; then
        echo -e "${YELLOW}⚠️  Electron app not built. Building now...${NC}"

        # Build the app
        echo -e "${BLUE}Building frontend...${NC}"
        pnpm run build || exit 1

        # Package for current platform
        echo -e "${BLUE}Packaging Electron app...${NC}"
        if [ "$ENVIRONMENT" = "docker" ] || [ "$(uname)" = "Linux" ]; then
            pnpm run electron-package:linux || exit 1
            app_path="release/linux-unpacked/atlasvibe"
        elif [ "$(uname)" = "Darwin" ]; then
            pnpm run electron-package:mac || exit 1
            app_path="release/mac/AtlasVibe.app/Contents/MacOS/AtlasVibe"
        else
            pnpm run electron-package:windows || exit 1
            app_path="release/win-unpacked/AtlasVibe.exe"
        fi
    fi

    export PLAYWRIGHT_ELECTRON_APP_PATH="$app_path"
    echo -e "${GREEN}✅ Using Electron app: $app_path${NC}"
}

# Function to run UI tests
run_ui_tests() {
    echo -e "${BLUE}🧪 Running UI tests...${NC}"

    # Create results directory
    mkdir -p test-results/ui

    # Set test configuration based on environment
    if [ "$ENVIRONMENT" = "docker" ]; then
        export HEADLESS=true
        export CI=true
        CONFIG="playwright.config.docker.electron.ts"
    else
        export HEADLESS=${HEADLESS:-false}
        CONFIG="playwright.config.ts"
    fi

    # Check if UI test file exists
    if [ ! -f playwright-test/ui-docker-tests.spec.ts ]; then
        echo -e "${RED}❌ UI test file not found: playwright-test/ui-docker-tests.spec.ts${NC}"
        exit 1
    fi

    # Install Playwright browsers if needed
    if [ ! -d ~/.cache/ms-playwright ]; then
        echo -e "${BLUE}Installing Playwright browsers...${NC}"
        pnpm exec playwright install chromium
    fi

    # Run the UI tests
    echo -e "${BLUE}Executing UI test suite...${NC}"

    if [ "$ENVIRONMENT" = "docker" ]; then
        # In Docker, use xvfb-run
        xvfb-run --auto-servernum --server-args="-screen 0 1920x1080x24" \
            pnpm exec playwright test \
                --config="$CONFIG" \
                --reporter=json \
                --reporter=html:test-results/ui/report \
                playwright-test/ui-docker-tests.spec.ts
    else
        # Local environment
        pnpm exec playwright test \
            --config="$CONFIG" \
            --reporter=json \
            --reporter=html:test-results/ui/report \
            --headed \
            playwright-test/ui-docker-tests.spec.ts
    fi

    TEST_EXIT_CODE=$?

    return $TEST_EXIT_CODE
}

# Function to generate report
generate_report() {
    echo -e "${BLUE}📊 Generating UI test report...${NC}"

    if [ -f run_ui_tests_report.py ]; then
        python3 run_ui_tests_report.py || echo -e "${YELLOW}Report generation failed${NC}"
    fi

    # Show summary
    if [ -f test-results/ui/results.json ]; then
        echo -e "\n${BLUE}Test Summary:${NC}"
        python3 -c "
import json
with open('test-results/ui/results.json') as f:
    data = json.load(f)
    stats = data.get('stats', {})
    print(f'Total: {stats.get(\"expected\", 0) + stats.get(\"unexpected\", 0)}')
    print(f'Passed: {stats.get(\"expected\", 0)}')
    print(f'Failed: {stats.get(\"unexpected\", 0)}')
        "
    fi
}

# Main execution
main() {
    echo -e "${BLUE}🖥️  AtlasVibe UI Test Runner${NC}"
    echo -e "${BLUE}============================${NC}"
    echo ""

    # Start virtual display if needed
    start_virtual_display

    # Check if app is built
    check_app_built

    # Run UI tests
    if run_ui_tests; then
        echo -e "\n${GREEN}✅ UI tests passed!${NC}"
        generate_report
        exit 0
    else
        echo -e "\n${RED}❌ UI tests failed!${NC}"
        generate_report
        exit 1
    fi
}

# Cleanup on exit
cleanup() {
    if [ -n "$XVFB_PID" ]; then
        kill $XVFB_PID 2>/dev/null || true
    fi
}

trap cleanup EXIT

# Run main
main "$@"

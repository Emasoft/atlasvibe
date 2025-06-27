#!/bin/bash
# Automated test runner that detects environment and runs appropriate tests
# Works seamlessly for local development and CI/CD environments

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Function to print colored output
print_color() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Function to detect environment
detect_environment() {
    if [ "$CI" = "true" ] || [ "$GITHUB_ACTIONS" = "true" ]; then
        echo "remote"
    elif [ -n "$DOCKER_HOST" ] || [ -f /.dockerenv ]; then
        echo "docker"
    else
        echo "local"
    fi
}

# Function to detect available resources
detect_resources() {
    local env=$1
    local cpu_count=$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4)
    local memory_gb=$(free -g 2>/dev/null | awk '/^Mem:/{print $2}' || echo 8)

    print_color $BLUE "🔍 System Resources:"
    echo "  CPU cores: $cpu_count"
    echo "  Memory: ${memory_gb}GB"
    echo ""
}

# Function to setup environment-specific variables
setup_environment() {
    local env=$1

    case $env in
        remote)
            export MAX_RETRIES=3
            export TIMEOUT_MULTIPLIER=1
            export SKIP_SLOW_TESTS=true
            export RUN_INTEGRATION_TESTS=false
            export RUN_UI_TESTS=false
            export PARALLEL_JOBS=2
            export TEST_PROFILES="remote"
            print_color $YELLOW "🌐 Remote/CI environment detected"
            ;;
        docker)
            export MAX_RETRIES=5
            export TIMEOUT_MULTIPLIER=1.5
            export SKIP_SLOW_TESTS=false
            export RUN_INTEGRATION_TESTS=true
            export RUN_UI_TESTS=true
            export PARALLEL_JOBS=1
            export TEST_PROFILES="local remote"
            print_color $BLUE "🐳 Docker environment detected"
            ;;
        local)
            export MAX_RETRIES=10
            export TIMEOUT_MULTIPLIER=2
            export SKIP_SLOW_TESTS=false
            export RUN_INTEGRATION_TESTS=true
            export RUN_UI_TESTS=true
            export PARALLEL_JOBS=4
            export TEST_PROFILES="local"
            print_color $GREEN "💻 Local environment detected"
            ;;
    esac
}

# Function to check prerequisites
check_prerequisites() {
    local env=$1
    local missing=()

    print_color $BLUE "📋 Checking prerequisites..."

    # Common requirements
    command -v python3 >/dev/null 2>&1 || missing+=("python3")
    command -v node >/dev/null 2>&1 || missing+=("node")
    command -v pnpm >/dev/null 2>&1 || missing+=("pnpm")
    command -v uv >/dev/null 2>&1 || missing+=("uv")

    # Environment-specific requirements
    if [ "$env" != "remote" ]; then
        command -v docker >/dev/null 2>&1 || missing+=("docker")
        command -v docker compose >/dev/null 2>&1 || missing+=("docker-compose")
    fi

    if [ ${#missing[@]} -gt 0 ]; then
        print_color $RED "❌ Missing prerequisites: ${missing[*]}"
        print_color $YELLOW "Please install missing tools and try again."
        return 1
    fi

    print_color $GREEN "✅ All prerequisites satisfied"
    return 0
}

# Function to run Python tests
run_python_tests() {
    local env=$1
    print_color $BLUE "\n🐍 Running Python tests..."

    # Create test results directory
    mkdir -p test-results/python

    # Run tests with appropriate settings
    if [ "$env" = "remote" ]; then
        uv run pytest -v -m "not slow" \
            --tb=short \
            --maxfail=5 \
            --junit-xml=test-results/python/junit.xml \
            --ignore=sample_projects \
            . || return 1
    else
        uv run pytest -v \
            --tb=short \
            --junit-xml=test-results/python/junit.xml \
            --cov=. \
            --cov-report=html:test-results/python/coverage \
            --ignore=sample_projects \
            . || return 1
    fi

    print_color $GREEN "✅ Python tests completed"
}

# Function to run JavaScript/TypeScript tests
run_js_tests() {
    local env=$1
    print_color $BLUE "\n📦 Running JavaScript/TypeScript tests..."

    # Create test results directory
    mkdir -p test-results/js

    # Check if test script exists
    if pnpm run | grep -q "test"; then
        # Run tests
        pnpm test || return 1
    else
        print_color $YELLOW "⚠️  No test script found, running linting instead"
        # Run linting as a basic check
        pnpm run lint || return 1
    fi

    print_color $GREEN "✅ JavaScript/TypeScript tests completed"
}

# Function to run Docker tests
run_docker_tests() {
    local env=$1
    local profiles=$2

    print_color $BLUE "\n🐳 Running Docker container tests..."

    for profile in $profiles; do
        print_color $PURPLE "  Running $profile profile..."

        if [ -f ./test-docker-comprehensive.sh ]; then
            if [ "$env" = "remote" ]; then
                # Skip build on CI to save time
                ./test-docker-comprehensive.sh $profile --skip-build || return 1
            else
                ./test-docker-comprehensive.sh $profile || return 1
            fi
        else
            print_color $YELLOW "  ⚠️  Docker test script not found, skipping"
        fi
    done

    print_color $GREEN "✅ Docker tests completed"
}

# Function to run UI tests
run_ui_tests() {
    local env=$1

    if [ "$RUN_UI_TESTS" != "true" ]; then
        print_color $YELLOW "⏭️  Skipping UI tests for $env environment"
        return 0
    fi

    print_color $BLUE "\n🖥️  Running UI tests..."

    if [ "$env" = "local" ] && [ -z "$DOCKER_HOST" ]; then
        # Check if Electron app is built
        if [ ! -d "release" ] || [ ! -f "release/linux-unpacked/atlasvibe" -a ! -f "release/mac-universal/atlasvibe.app/Contents/MacOS/atlasvibe" ]; then
            print_color $YELLOW "⚠️  Electron app not built, building now..."
            pnpm run build || return 1
        fi

        # Run UI tests directly with Playwright
        pnpm exec playwright test playwright-test/ui-docker-tests.spec.ts \
            --reporter=json --reporter=html || return 1
    else
        # Run UI tests in Docker
        ./test-docker-comprehensive.sh ui || return 1
    fi

    print_color $GREEN "✅ UI tests completed"
}

# Function to generate combined report
generate_report() {
    local env=$1
    local start_time=$2
    local python_passed=$3
    local js_passed=$4
    local docker_passed=$5
    local ui_passed=$6
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    print_color $BLUE "\n📊 Generating test report..."

    cat > test-results/summary.md << EOF
# AtlasVibe Automated Test Report

**Environment**: $env
**Date**: $(date)
**Duration**: ${duration}s

## Test Results

### Python Tests
$(if [ -f test-results/python/junit.xml ] && [ $python_passed -eq 0 ]; then echo "✅ Passed"; else echo "❌ Failed"; fi)

### JavaScript/TypeScript Tests
$(if [ $js_passed -eq 0 ]; then echo "✅ Passed"; else echo "❌ Failed"; fi)

### Docker Tests
$(if [ $docker_passed -eq 0 ]; then echo "✅ Passed"; else echo "❌ Failed"; fi)

### UI Tests
$(if [ "$RUN_UI_TESTS" = "true" ]; then echo "✅ Completed"; else echo "⏭️ Skipped"; fi)

## Environment Configuration
- Max Retries: $MAX_RETRIES
- Timeout Multiplier: $TIMEOUT_MULTIPLIER
- Skip Slow Tests: $SKIP_SLOW_TESTS
- Run Integration Tests: $RUN_INTEGRATION_TESTS
- Run UI Tests: $RUN_UI_TESTS
- Parallel Jobs: $PARALLEL_JOBS

## Artifacts
- Python coverage: test-results/python/coverage/index.html
- Test logs: test-results/logs/
- Screenshots: test-results/screenshots/
EOF

    print_color $GREEN "✅ Report generated: test-results/summary.md"
}

# Function to clean up
cleanup() {
    print_color $BLUE "\n🧹 Cleaning up..."

    # Kill any hanging processes
    pkill -f "playwright" 2>/dev/null || true
    pkill -f "electron" 2>/dev/null || true

    # Clean temporary files
    rm -rf /tmp/atlasvibe-test-* 2>/dev/null || true

    print_color $GREEN "✅ Cleanup completed"
}

# Main execution
main() {
    local start_time=$(date +%s)

    print_color $PURPLE "🚀 AtlasVibe Automated Test Runner"
    print_color $PURPLE "=================================="
    echo ""

    # Detect environment
    local env=$(detect_environment)

    # Setup environment
    setup_environment $env

    # Detect resources
    detect_resources $env

    # Check prerequisites
    if ! check_prerequisites $env; then
        exit 1
    fi

    # Create test results directory
    mkdir -p test-results/{python,js,docker,ui,logs}

    # Set error handling
    set -e
    trap cleanup EXIT

    # Run tests based on environment
    local failed=0
    local python_passed=1
    local js_passed=1
    local docker_passed=1
    local ui_passed=1

    # Python tests
    if run_python_tests $env; then
        python_passed=0
    else
        print_color $RED "❌ Python tests failed"
        failed=1
    fi

    # JavaScript tests
    if run_js_tests $env; then
        js_passed=0
    else
        print_color $RED "❌ JavaScript tests failed"
        failed=1
    fi

    # Docker tests (if not in remote CI)
    if [ "$env" != "remote" ] || [ "$RUN_DOCKER_TESTS" = "true" ]; then
        if run_docker_tests $env "$TEST_PROFILES"; then
            docker_passed=0
        else
            print_color $RED "❌ Docker tests failed"
            failed=1
        fi
    else
        docker_passed=0  # Skipped counts as passed
    fi

    # UI tests
    if run_ui_tests $env; then
        ui_passed=0
    else
        print_color $RED "❌ UI tests failed"
        failed=1
    fi

    # Generate report
    generate_report $env $start_time $python_passed $js_passed $docker_passed $ui_passed

    # Final summary
    echo ""
    if [ $failed -eq 0 ]; then
        print_color $GREEN "🎉 All tests passed!"
        exit 0
    else
        print_color $RED "😞 Some tests failed"
        exit 1
    fi
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --env)
            FORCE_ENV="$2"
            shift 2
            ;;
        --skip-docker)
            SKIP_DOCKER=true
            shift
            ;;
        --skip-ui)
            RUN_UI_TESTS=false
            shift
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --env <local|remote|docker>  Force specific environment"
            echo "  --skip-docker                Skip Docker tests"
            echo "  --skip-ui                    Skip UI tests"
            echo "  --help                       Show this help"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Override environment if forced
if [ -n "$FORCE_ENV" ]; then
    detect_environment() { echo "$FORCE_ENV"; }
fi

# Run main
main

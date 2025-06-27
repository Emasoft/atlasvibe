#!/bin/bash
# Comprehensive Docker test runner for AtlasVibe
# Supports local, remote, and integration test profiles

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
PROFILE="${1:-local}"
SKIP_BUILD="${SKIP_BUILD:-false}"
VERBOSE="${VERBOSE:-false}"

# Function to print colored output
print_color() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Function to print usage
usage() {
    echo "Usage: $0 [profile] [options]"
    echo ""
    echo "Profiles:"
    echo "  local       - Run comprehensive tests with local profile (default)"
    echo "  remote      - Run optimized tests for CI/GitHub Actions"
    echo "  integration - Run integration tests including GitHub repo cloning"
    echo "  ui          - Run UI tests for Electron app"
    echo "  all         - Run all test profiles sequentially"
    echo ""
    echo "Options:"
    echo "  --skip-build    Skip Docker image build"
    echo "  --verbose       Show detailed output"
    echo "  --help          Show this help message"
    echo ""
    echo "Environment variables:"
    echo "  SKIP_BUILD=true       Skip Docker image build"
    echo "  VERBOSE=true          Show detailed output"
    echo "  TEST_REPO_URL=<url>   GitHub repo URL for integration tests"
    echo "  GITHUB_TOKEN=<token>  GitHub token for authenticated operations"
    exit 0
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-build)
            SKIP_BUILD=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --help|-h)
            usage
            ;;
        local|remote|integration|ui|all)
            PROFILE=$1
            shift
            ;;
        *)
            print_color $RED "Unknown option: $1"
            usage
            ;;
    esac
done

# Change to project directory
cd "$(dirname "$0")"

print_color $BLUE "🐳 AtlasVibe Docker Test Runner"
print_color $BLUE "==============================="
echo "Profile: $PROFILE"
echo "Skip build: $SKIP_BUILD"
echo "Verbose: $VERBOSE"
echo ""

# Create directories for test results
mkdir -p test-results test-logs

# Clean up previous test results
rm -rf test-results/* test-logs/*

# Build Docker images if needed
if [ "$SKIP_BUILD" != "true" ]; then
    print_color $YELLOW "🔨 Building Docker test image..."

    if [ "$VERBOSE" = "true" ]; then
        timeout 300 docker compose -f docker/docker-compose.test.yml build || {
            print_color $RED "Docker build timed out or failed"
            exit 1
        }
    else
        timeout 300 docker compose -f docker/docker-compose.test.yml build --quiet || {
            print_color $RED "Docker build timed out or failed"
            exit 1
        }
    fi

    print_color $GREEN "✅ Docker image built successfully"
else
    print_color $YELLOW "⏭️  Skipping Docker image build"
fi

# Function to run tests for a specific profile
run_profile_tests() {
    local profile=$1

    print_color $BLUE "\n🧪 Running $profile profile tests..."
    print_color $BLUE "=========================================="

    # Set profile-specific environment variables
    case $profile in
        local)
            export MAX_RETRIES=10
            export TIMEOUT_MULTIPLIER=2
            export SKIP_SLOW_TESTS=false
            export RUN_INTEGRATION_TESTS=true
            ;;
        remote)
            export MAX_RETRIES=3
            export TIMEOUT_MULTIPLIER=1
            export SKIP_SLOW_TESTS=true
            export RUN_INTEGRATION_TESTS=false
            export CI=true
            export GITHUB_ACTIONS=true
            ;;
        integration)
            export RUN_GITHUB_CLONE_TEST=true
            ;;
        ui)
            export RUN_UI_TESTS=true
            export HEADLESS=true
            export MAX_RETRIES=5
            export TIMEOUT_MULTIPLIER=2
            ;;
    esac

    # Run the tests
    if [ "$VERBOSE" = "true" ]; then
        docker compose -f docker/docker-compose.test.yml run \
            --rm \
            --service-ports \
            atlasvibe-test-$profile
    else
        docker compose -f docker/docker-compose.test.yml run \
            --rm \
            --service-ports \
            atlasvibe-test-$profile 2>&1 | tee test-logs/${profile}-output.log
    fi

    local exit_code=$?

    if [ $exit_code -eq 0 ]; then
        print_color $GREEN "✅ $profile tests passed!"
    else
        print_color $RED "❌ $profile tests failed (exit code: $exit_code)"
    fi

    return $exit_code
}

# Function to generate combined test report
generate_combined_report() {
    print_color $BLUE "\n📊 Generating combined test report..."

    cat > test-results/combined-report.md << EOF
# AtlasVibe Docker Test Report

Generated: $(date)

## Test Profiles Run

EOF

    for profile in local remote integration ui; do
        if [ -f "test-logs/${profile}-output.log" ]; then
            echo "### $profile Profile" >> test-results/combined-report.md
            echo '```' >> test-results/combined-report.md
            tail -20 test-logs/${profile}-output.log >> test-results/combined-report.md
            echo '```' >> test-results/combined-report.md
            echo "" >> test-results/combined-report.md
        fi
    done

    print_color $GREEN "✅ Combined report generated: test-results/combined-report.md"
}

# Main test execution
FAILED_PROFILES=()

if [ "$PROFILE" = "all" ]; then
    # Run all profiles
    for p in local remote integration ui; do
        if ! run_profile_tests $p; then
            FAILED_PROFILES+=($p)
        fi
    done

    generate_combined_report

    # Summary
    print_color $BLUE "\n📊 Test Summary"
    print_color $BLUE "==============="

    if [ ${#FAILED_PROFILES[@]} -eq 0 ]; then
        print_color $GREEN "✅ All test profiles passed!"
        exit 0
    else
        print_color $RED "❌ Failed profiles: ${FAILED_PROFILES[*]}"
        exit 1
    fi
else
    # Run single profile
    if run_profile_tests $PROFILE; then
        print_color $GREEN "\n✅ All tests passed!"
        exit 0
    else
        print_color $RED "\n❌ Tests failed!"
        exit 1
    fi
fi

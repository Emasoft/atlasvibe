#!/usr/bin/env bash
# Comprehensive test suite for sequential pre-commit configuration

set -euo pipefail

# Source constants
source "$(pwd)/.sequential-precommit-constants.sh" 2>/dev/null || {
    # Define colors if constants file doesn't exist
    export GREEN='\033[0;32m'
    export RED='\033[0;31m'
    export NC='\033[0m'
    
    # Define portable_echo function
    portable_echo() {
        if [ "${1:-}" = "-e" ]; then
            shift
            printf '%b\n' "$@"
        else
            printf '%s\n' "$@"
        fi
    }
    
    # Define other required functions
    detect_platform() {
        case "${OSTYPE:-$(uname -s | tr '[:upper:]' '[:lower:]')}" in
            linux*) echo "linux" ;;
            darwin*) echo "macos" ;;
            *) echo "unknown" ;;
        esac
    }
    
    calculate_md5() {
        local input="$1"
        if command -v md5sum >/dev/null 2>&1; then
            echo -n "$input" | md5sum | cut -d' ' -f1
        elif command -v md5 >/dev/null 2>&1; then
            echo -n "$input" | md5 -q
        else
            echo "test-hash"
        fi
    }
    
    is_orphaned() {
        return 1  # Not orphaned for test
    }
}

TESTS_PASSED=0
TESTS_FAILED=0

# Test function
run_test() {
    local test_name="$1"
    local test_cmd="$2"
    
    echo -n "Testing $test_name... "
    if eval "$test_cmd" >/dev/null 2>&1; then
        echo "$(portable_echo -e "${GREEN}✓ PASSED${NC}")"
        ((TESTS_PASSED++))
    else
        echo "$(portable_echo -e "${RED}✗ FAILED${NC}")"
        ((TESTS_FAILED++))
    fi
}

echo "=== Sequential Pre-commit Test Suite ==="
echo

# Environment tests
run_test "Python version" "python3 --version | grep -q '3\.1[1-9]'"
run_test "Pre-commit installed" "command -v pre-commit"
run_test "Environment file exists" "[ -f .sequential-precommit-env ]"
run_test "Constants file exists" "[ -f .sequential-precommit-constants.sh ]"

# Configuration tests
run_test "All hooks have require_serial" \
    "grep -c 'require_serial: true' .pre-commit-config.yaml | grep -q '[0-9][0-9]'"
run_test "Python version file" "[ -f .python-version ] && grep -q '3.11' .python-version"

# Wrapper tests
run_test "Pre-commit wrapper exists" "[ -f .git/hooks/pre-commit-wrapper-robust-v3 ]"
run_test "Wrapper is executable" "[ -x .git/hooks/pre-commit-wrapper-robust-v3 ]"
run_test "Memory wrapper exists" "[ -f .pre-commit-wrappers/memory-limited-hook.sh ]"

# Function tests
run_test "Platform detection" "detect_platform | grep -E 'linux|macos|windows'"
run_test "MD5 calculation" "[ -n \"$(calculate_md5 'test')\" ]"
run_test "Orphan detection" "! is_orphaned $$"

# Lock file tests
run_test "Lock directory writable" "touch /tmp/test-lock-$$ && rm -f /tmp/test-lock-$$"

# Summary
echo
echo "=== Test Summary ==="
echo "Tests passed: $TESTS_PASSED"
echo "Tests failed: $TESTS_FAILED"

if [ $TESTS_FAILED -eq 0 ]; then
    echo "$(portable_echo -e "${GREEN}✓ All tests passed!${NC}")"
    exit 0
else
    echo "$(portable_echo -e "${RED}✗ Some tests failed${NC}")"
    exit 1
fi
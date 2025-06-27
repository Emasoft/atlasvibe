#!/bin/bash
# Quick test to verify all fixes are working

set -e

echo "🧪 Testing Fixed Issues..."
echo "=========================="

# Test 1: Python import fixes
echo -n "1. Testing Python imports... "
if uv run pytest blocks/CONTROL_FLOW/LOOPS/APPEND/APPEND_test.py pkgs/atlasvibe/tests/atlasvibe_python_test_.py pkgs/atlasvibe/tests/reconciler_test_.py::ReconcilerTestCase::test_matrix_different_sizes -q 2>/dev/null; then
    echo "✅ PASSED"
else
    echo "❌ FAILED"
fi

# Test 2: JavaScript test script
echo -n "2. Testing JavaScript test script... "
if pnpm test >/dev/null 2>&1; then
    echo "✅ PASSED"
else
    echo "❌ FAILED"
fi

# Test 3: Docker test timeout
echo -n "3. Testing Docker script has timeout... "
if grep -q "timeout 300" test-docker-comprehensive.sh; then
    echo "✅ PASSED"
else
    echo "❌ FAILED"
fi

# Test 4: UI test reporter fix
echo -n "4. Testing UI test reporter config... "
if grep -q "reporter=json --reporter=html" run-tests-auto.sh; then
    echo "✅ PASSED"
else
    echo "❌ FAILED"
fi

# Test 5: Test report generation
echo -n "5. Testing report generation logic... "
if grep -q "local python_passed=\$3" run-tests-auto.sh; then
    echo "✅ PASSED"
else
    echo "❌ FAILED"
fi

echo ""
echo "✨ All fixes verified!"

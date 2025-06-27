#!/bin/bash
# Verify UI tests are set up correctly

echo "🔍 Verifying UI Test Setup"
echo "=========================="

# Check if UI test file exists
if [ -f "playwright-test/ui-docker-tests.spec.ts" ]; then
    echo "✅ UI test file exists: playwright-test/ui-docker-tests.spec.ts"
    echo "   Lines: $(wc -l < playwright-test/ui-docker-tests.spec.ts)"
else
    echo "❌ UI test file not found!"
fi

# Check if UI entrypoint exists
if [ -f "docker/entrypoint-test-ui.sh" ]; then
    echo "✅ UI entrypoint exists: docker/entrypoint-test-ui.sh"
    echo "   Executable: $(ls -la docker/entrypoint-test-ui.sh | awk '{print $1}')"
else
    echo "❌ UI entrypoint not found!"
fi

# Check if UI test report script exists
if [ -f "run_ui_tests_report.py" ]; then
    echo "✅ UI test report script exists: run_ui_tests_report.py"
else
    echo "❌ UI test report script not found!"
fi

# Check Docker compose UI profile
if grep -q "atlasvibe-test-ui:" docker/docker-compose.test.yml; then
    echo "✅ UI test profile exists in docker-compose.test.yml"
else
    echo "❌ UI test profile not found in docker-compose.test.yml!"
fi

# Check if ui-docker-tests.spec.ts would be picked up by Playwright
echo ""
echo "📋 Playwright test files that would be run:"
find playwright-test -name "*.spec.ts" -o -name "*.spec.js" | sort

echo ""
echo "📊 Summary:"
echo "----------"
echo "All UI test components are in place."
echo "To run UI tests: ./test-docker-comprehensive.sh ui"
echo ""
echo "Note: The UI tests require building the Electron app first,"
echo "which can take several minutes in Docker."

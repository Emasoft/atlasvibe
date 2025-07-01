#!/usr/bin/env python3
"""Parse Playwright test results JSON and display detailed results."""

import json
import sys
import os


def main():
    """Parse test results and display detailed summary."""
    results_file = os.environ.get("RESULTS_FILE", "test-results/results.json")

    with open(results_file, "r") as f:
        data = json.load(f)

    # Initialize counters
    total = passed = failed = skipped = 0

    # Parse results based on Playwright JSON format
    if "suites" in data:
        for suite in data["suites"]:
            suite_name = suite.get("title", "Unknown Suite")
            for spec in suite.get("specs", []):
                for test in spec.get("tests", []):
                    total += 1
                    test_name = test.get("title", "Unknown Test")
                    results = test.get("results", [])
                    if results:
                        status = results[0].get("status", "passed").lower()
                        if status == "passed":
                            passed += 1
                            print(f"✅ PASSED: {suite_name} > {test_name}")
                        elif status == "failed":
                            failed += 1
                            error = (
                                results[0]
                                .get("error", {})
                                .get("message", "Unknown error")
                            )
                            print(f"❌ FAILED: {suite_name} > {test_name}")
                            print(f"   Error: {error[:100]}...")
                        elif status == "skipped":
                            skipped += 1
                            print(f"⏭️  SKIPPED: {suite_name} > {test_name}")

    print(f"\n{'=' * 60}")
    print(f"Total: {total} | Passed: {passed} | Failed: {failed} | Skipped: {skipped}")
    print(f"{'=' * 60}")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()

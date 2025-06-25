#!/usr/bin/env python3
"""Parse Playwright test results JSON and display summary."""

import json
import sys
import os


def main():
    """Parse test results and display summary."""
    results_file = os.environ.get("RESULTS_FILE", "test-results/results.json")

    try:
        with open(results_file, "r") as f:
            data = json.load(f)

        # Count results
        total = 0
        passed = 0
        failed = 0
        skipped = 0

        if "suites" in data:
            for suite in data["suites"]:
                for spec in suite.get("specs", []):
                    for test in spec.get("tests", []):
                        total += 1
                        results = test.get("results", [])
                        if results:
                            status = results[0].get("status", "passed").lower()
                            if status == "passed":
                                passed += 1
                            elif status == "failed":
                                failed += 1
                            elif status == "skipped":
                                skipped += 1

        print(f"Total Tests: {total}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"⏭️  Skipped: {skipped}")

        if failed > 0:
            print(f"\n😞 {failed} tests failed!")
            sys.exit(1)
        else:
            print("\n🎉 All tests passed!")

    except Exception as e:
        print(f"Error parsing results: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

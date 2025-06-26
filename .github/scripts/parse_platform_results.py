#!/usr/bin/env python3
"""Parse platform-specific test results."""

import json
import os
import sys


def main():
    """Parse test results for a specific platform."""
    platform = os.environ.get("PLATFORM", "unknown")

    try:
        with open("test-results/results.json", "r") as f:
            data = json.load(f)

        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        skipped_tests = 0

        # Parse the results based on Playwright's JSON reporter format
        if "suites" in data:
            for suite in data["suites"]:
                for spec in suite.get("specs", []):
                    for test in spec.get("tests", []):
                        total_tests += 1
                        results = test.get("results", [])
                        if results:
                            status = results[0].get("status", "unknown").lower()
                            if status == "passed":
                                passed_tests += 1
                            elif status == "failed":
                                failed_tests += 1
                            elif status == "skipped":
                                skipped_tests += 1

        print(f"Platform: {platform}")
        print(f"Total tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"⏭️  Skipped: {skipped_tests}")

        if failed_tests > 0:
            sys.exit(1)

    except FileNotFoundError:
        print(f"❌ No test results file found for platform: {platform}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse test results JSON: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

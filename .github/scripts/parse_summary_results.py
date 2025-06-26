#!/usr/bin/env python3
"""Parse summary results for multiple platforms."""

import json
import os
import sys


def main():
    """Parse results for summary report."""
    results_dir = os.environ.get("RESULTS_DIR", "")

    if not results_dir:
        print("❌ RESULTS_DIR environment variable not set")
        sys.exit(1)

    try:
        with open(f"{results_dir}/results.json", "r") as f:
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

        # Output markdown format for summary
        print(f"- Total: {total_tests}")
        print(f"- ✅ Passed: {passed_tests}")
        print(f"- ❌ Failed: {failed_tests}")
        print(f"- ⏭️  Skipped: {skipped_tests}")

        if total_tests == 0:
            print("- ⚠️  No tests were run")
        elif failed_tests == 0 and passed_tests > 0:
            print("- 🎉 All tests passed!")
        elif failed_tests > 0:
            print(f"- ⚠️  {failed_tests} test(s) failed")

    except FileNotFoundError:
        print("❌ No test results file found")
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse test results JSON: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


if __name__ == "__main__":
    main()

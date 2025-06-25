#!/usr/bin/env python3
"""Parse E2E test results."""

import json
import sys


def main():
    """Parse E2E test results."""
    results_file = "test-results/results.json"

    with open(results_file, "r") as f:
        data = json.load(f)

    total = passed = failed = skipped = 0

    # Parse Playwright JSON results
    for suite in data.get("suites", []):
        for spec in suite.get("specs", []):
            for test in spec.get("tests", []):
                total += 1
                results = test.get("results", [])
                if results:
                    status = results[0].get("status", "").lower()
                    if status == "passed":
                        passed += 1
                    elif status == "failed":
                        failed += 1
                        error = results[0].get("error", {}).get("message", "")
                        print(f"❌ {test.get('title', 'Unknown')}: {error[:80]}...")
                    elif status == "skipped":
                        skipped += 1

    print(f"\nTotal: {total}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"⏭️  Skipped: {skipped}")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()

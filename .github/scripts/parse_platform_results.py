#!/usr/bin/env python3
"""Parse platform-specific test results."""

import json
import os


def main():
    """Parse test results for a specific platform."""
    platform = os.environ.get("PLATFORM", "unknown")

    with open("test-results/results.json", "r") as f:
        json.load(f)  # Load but don't use for now
        print(f"Platform: {platform}")
        # Add result parsing logic here if needed


if __name__ == "__main__":
    main()

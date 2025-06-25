#!/usr/bin/env python3
"""Parse summary results for multiple platforms."""

import json
import os


def main():
    """Parse results for summary report."""
    results_dir = os.environ.get("RESULTS_DIR", "")

    with open(f"{results_dir}/results.json", "r") as f:
        json.load(f)  # Load but don't use for now
        # Parse and add results to summary
        # This could be expanded with more detailed parsing if needed


if __name__ == "__main__":
    main()

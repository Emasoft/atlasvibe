#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fix duplicate concurrency blocks in GitHub Actions workflows."""

import re
from pathlib import Path


def fix_duplicate_concurrency(filepath: Path) -> None:
    """Remove duplicate concurrency blocks from a workflow file."""
    with open(filepath, "r") as f:
        content = f.read()

    # Count occurrences of concurrency blocks
    concurrency_matches = list(
        re.finditer(
            r"^concurrency:\n  group:.*\n  cancel-in-progress:.*\n",
            content,
            re.MULTILINE,
        )
    )

    if len(concurrency_matches) > 1:
        print(f"  Found {len(concurrency_matches)} concurrency blocks in {filepath.name}, removing duplicates...")

        # Keep only the first concurrency block
        # Remove all but the first occurrence
        for match in reversed(concurrency_matches[1:]):
            content = content[: match.start()] + content[match.end() :]

        with open(filepath, "w") as f:
            f.write(content)
        print(f"  ✓ Fixed {filepath.name}")
    else:
        print(f"  ✓ {filepath.name} is OK")


def main() -> None:
    """Process all workflow files."""
    workflows_dir = Path(".github/workflows")

    print("🔧 Fixing duplicate concurrency blocks...")
    print("=" * 40)

    for workflow_file in sorted(workflows_dir.glob("*.yml")) + sorted(workflows_dir.glob("*.yaml")):
        fix_duplicate_concurrency(workflow_file)

    print("\n✅ Done!")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fix incorrectly placed timeouts in GitHub Actions workflows."""

import re
from pathlib import Path


def fix_workflow_timeouts(filepath: Path) -> bool:
    """Remove timeouts from event triggers and ensure they're only on jobs."""
    with open(filepath, "r") as f:
        content = f.read()

    original_content = content

    # Remove timeout-minutes from event triggers (they don't belong there)
    # Pattern: event name followed by timeout-minutes on next line
    content = re.sub(
        r"(^\s+\w+:\s*\n)\s+timeout-minutes:\s*\d+\s*\n",
        r"\1",
        content,
        flags=re.MULTILINE,
    )

    # Also remove timeout-minutes that appear in the wrong place in the 'on:' section
    # Pattern: under 'on:' section before any job definitions
    lines = content.split("\n")
    in_on_section = False
    in_jobs_section = False
    cleaned_lines = []

    for line in lines:
        if line.strip() == "on:":
            in_on_section = True
            in_jobs_section = False
        elif line.strip() == "jobs:":
            in_on_section = False
            in_jobs_section = True

        # Skip timeout-minutes lines in the 'on:' section
        if in_on_section and "timeout-minutes:" in line:
            continue

        cleaned_lines.append(line)

    content = "\n".join(cleaned_lines)

    # Remove duplicate timeout-minutes from jobs
    # Pattern: job with multiple timeout-minutes entries
    content = re.sub(
        r"(timeout-minutes:\s*\d+\s*\n)(\s*timeout-minutes:\s*\d+\s*\n)+",
        r"\1",
        content,
        flags=re.MULTILINE,
    )

    if content != original_content:
        with open(filepath, "w") as f:
            f.write(content)
        return True

    return False


def main() -> None:
    """Process all workflow files."""
    workflows_dir = Path(".github/workflows")

    print("🔧 Fixing incorrectly placed timeouts in workflows...")
    print("=" * 50)

    fixed_count = 0

    for workflow_file in sorted(workflows_dir.glob("*.yml")) + sorted(
        workflows_dir.glob("*.yaml")
    ):
        if fix_workflow_timeouts(workflow_file):
            print(f"  ✓ Fixed {workflow_file.name}")
            fixed_count += 1

    print("\n" + "=" * 50)
    print(f"✅ Fixed {fixed_count} workflow files!")


if __name__ == "__main__":
    main()

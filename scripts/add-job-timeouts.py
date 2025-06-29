#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Add job-level timeouts to GitHub Actions workflows."""

import re
from pathlib import Path
from typing import Dict, List, Tuple

# Default timeouts for different job types
TIMEOUT_RULES = {
    # Job name patterns and their timeouts
    "test": 30,
    "e2e": 30,
    "build": 45,
    "deploy": 60,
    "lint": 10,
    "format": 10,
    "check": 15,
    "docker": 30,
    "matrix": 30,
    "security": 15,
    "dependency": 20,
    "actionlint": 10,
    "gitleaks": 10,
    "pre-commit": 20,
    "summary": 10,
}


def get_timeout_for_job(job_name: str) -> int:
    """Determine appropriate timeout based on job name."""
    job_lower = job_name.lower()

    # Check each pattern
    for pattern, timeout in TIMEOUT_RULES.items():
        if pattern in job_lower:
            return timeout

    # Default timeout
    return 20


def add_timeouts_to_workflow(filepath: Path) -> Tuple[bool, List[str]]:
    """Add timeouts to jobs in a workflow file."""
    with open(filepath, "r") as f:
        lines = f.readlines()

    modified = False
    changes = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Look for job definitions (2 spaces + job_name + colon)
        if re.match(r"^  \w+:\s*$", line):
            job_name = line.strip().rstrip(":")

            # Check if the next few lines already have timeout-minutes
            has_timeout = False
            for j in range(i + 1, min(i + 10, len(lines))):
                if "timeout-minutes:" in lines[j]:
                    has_timeout = True
                    break
                # Stop if we hit another job or the jobs section ends
                if re.match(r"^  \w+:\s*$", lines[j]) or re.match(r"^\w+:", lines[j]):
                    break

            if not has_timeout:
                # Find where to insert timeout-minutes
                # Look for the line after the job name that isn't indented more
                insert_idx = i + 1

                # Skip any job-level configuration until we find a good insertion point
                while insert_idx < len(lines):
                    next_line = lines[insert_idx]
                    # If it's a property at the job level (4 spaces), keep looking
                    if re.match(r"^    \w+:", next_line):
                        insert_idx += 1
                    else:
                        break

                # Determine timeout
                timeout = get_timeout_for_job(job_name)

                # Insert timeout-minutes
                timeout_line = f"    timeout-minutes: {timeout}\n"

                # Insert after job name but try to maintain order
                # (usually: name, runs-on, timeout-minutes, strategy, etc.)
                best_insert_idx = i + 1
                for j in range(i + 1, min(i + 10, len(lines))):
                    if re.match(r"^    runs-on:", lines[j]):
                        best_insert_idx = j + 1
                        break
                    elif re.match(r"^    name:", lines[j]):
                        continue  # Keep looking
                    elif re.match(r"^    strategy:", lines[j]) or re.match(r"^    steps:", lines[j]):
                        best_insert_idx = j
                        break

                lines.insert(best_insert_idx, timeout_line)
                modified = True
                changes.append(f"Added timeout-minutes: {timeout} to job '{job_name}'")
                i = best_insert_idx  # Skip the line we just inserted

        i += 1

    if modified:
        with open(filepath, "w") as f:
            f.writelines(lines)

    return modified, changes


def main():
    """Process all workflow files."""
    workflows_dir = Path(".github/workflows")

    print("🔧 Adding job-level timeouts to workflows...")
    print("=" * 50)

    total_changes = 0

    for workflow_file in sorted(workflows_dir.glob("*.yml")) + sorted(workflows_dir.glob("*.yaml")):
        modified, changes = add_timeouts_to_workflow(workflow_file)

        if modified:
            print(f"\n📝 {workflow_file.name}:")
            for change in changes:
                print(f"  ✓ {change}")
            total_changes += len(changes)
        else:
            print(f"✓ {workflow_file.name} - all jobs have timeouts")

    print("\n" + "=" * 50)
    print(f"✅ Added {total_changes} timeout configurations!")

    if total_changes > 0:
        print("\n📋 Next steps:")
        print("1. Review the changes: git diff .github/workflows/")
        print("2. Adjust any timeouts that seem too short or too long")
        print("3. Commit the changes")


if __name__ == "__main__":
    main()

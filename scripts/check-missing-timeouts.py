#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Check for jobs missing timeout-minutes in GitHub Actions workflows."""

import re
from pathlib import Path
from typing import Dict, List, Tuple


def check_workflow_timeouts(filepath: Path) -> List[str]:
    """Check which jobs are missing timeout-minutes."""
    with open(filepath, "r") as f:
        content = f.read()

    missing_timeouts: List[str] = []

    # Find the jobs section
    jobs_match = re.search(r"^jobs:\s*$", content, re.MULTILINE)
    if not jobs_match:
        return missing_timeouts

    # Find all job definitions
    job_pattern = r"^  (\w+):\s*$"
    job_matches = list(
        re.finditer(job_pattern, content[jobs_match.end() :], re.MULTILINE)
    )

    for i, match in enumerate(job_matches):
        job_name = match.group(1)
        job_start = jobs_match.end() + match.start()

        # Find the end of this job (start of next job or end of file)
        if i < len(job_matches) - 1:
            job_end = jobs_match.end() + job_matches[i + 1].start()
        else:
            job_end = len(content)

        job_content = content[job_start:job_end]

        # Check if this job has timeout-minutes
        if "timeout-minutes:" not in job_content:
            missing_timeouts.append(job_name)

    return missing_timeouts


def main() -> None:
    """Check all workflow files."""
    workflows_dir = Path(".github/workflows")

    print("🔍 Checking for jobs without timeout-minutes...")
    print("=" * 50)

    total_missing = 0

    for workflow_file in sorted(workflows_dir.glob("*.yml")) + sorted(
        workflows_dir.glob("*.yaml")
    ):
        missing = check_workflow_timeouts(workflow_file)

        if missing:
            print(f"\n❌ {workflow_file.name}:")
            for job in missing:
                print(f"   - Job '{job}' is missing timeout-minutes")
            total_missing += len(missing)
        else:
            print(f"✓ {workflow_file.name} - all jobs have timeouts")

    print("\n" + "=" * 50)
    print(f"Total jobs missing timeouts: {total_missing}")


if __name__ == "__main__":
    main()

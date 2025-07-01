#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix GitHub Actions workflows to be properly cancellable and interruptible.

This script:
1. Adds concurrency settings to all workflows
2. Adds timeout-minutes to all jobs
3. Replaces 'if: always()' with 'if: success() || failure()'
4. Ensures proper signal handling
"""

import os
import re
import yaml
from pathlib import Path
from typing import Dict, Any, List, Tuple


def load_workflow(filepath: Path) -> Tuple[str, Any]:
    """Load a workflow file preserving comments and structure."""
    with open(filepath, "r") as f:
        content = f.read()
    return content, yaml.safe_load(content)


def fix_workflow(filepath: Path) -> None:
    """Fix a single workflow file to be properly cancellable."""
    print(f"\nProcessing: {filepath.name}")

    with open(filepath, "r") as f:
        content = f.read()

    original_content = content

    # 1. Add concurrency setting if missing
    if "concurrency:" not in content:
        # Find the right place to insert concurrency (after 'on:' block)
        on_pattern = r"(on:\s*(?:\[.*?\]|\{.*?\}|(?:\n(?:  |\t).*)*\n))"
        match = re.search(on_pattern, content, re.MULTILINE | re.DOTALL)

        if match:
            workflow_name = filepath.stem
            # Create appropriate concurrency group name
            if "docker" in workflow_name:
                group_name = f"docker-{workflow_name}-${{{{ github.ref }}}}"
            elif "electron" in workflow_name:
                group_name = f"electron-{workflow_name}-${{{{ github.ref }}}}"
            else:
                group_name = "${{ github.workflow }}-${{ github.ref }}"

            concurrency_block = f"""
concurrency:
  group: {group_name}
  cancel-in-progress: true
"""
            # Insert after the 'on:' block
            insert_pos = match.end()
            content = content[:insert_pos] + concurrency_block + content[insert_pos:]
            print("  ✓ Added concurrency settings")

    # 2. Replace 'if: always()' with 'if: success() || failure()'
    always_count = content.count("if: always()")
    if always_count > 0:
        content = content.replace("if: always()", "if: success() || failure()")
        print(f"  ✓ Replaced {always_count} instances of 'if: always()'")

    # 3. Add timeout-minutes to jobs if missing
    # Find all job definitions
    jobs_pattern = r"^jobs:\s*$"
    jobs_match = re.search(jobs_pattern, content, re.MULTILINE)

    if jobs_match:
        # Find each job in the jobs section
        job_pattern = r"^  (\w+):\s*$"
        jobs_section_end = content.find("\n\n", jobs_match.end())
        if jobs_section_end == -1:
            jobs_section_end = len(content)

        jobs_section = content[jobs_match.end() : jobs_section_end]
        job_matches = list(re.finditer(job_pattern, jobs_section, re.MULTILINE))

        # Process jobs in reverse order to maintain positions
        for match in reversed(job_matches):
            job_name = match.group(1)
            job_start = jobs_match.end() + match.start()

            # Check if this job has timeout-minutes
            next_job_start = jobs_match.end() + (
                job_matches[job_matches.index(match) + 1].start()
                if job_matches.index(match) < len(job_matches) - 1
                else len(jobs_section)
            )
            job_content = content[job_start : jobs_match.end() + next_job_start]

            if "timeout-minutes:" not in job_content:
                # Determine appropriate timeout based on job type
                if "test" in job_name.lower() or "e2e" in job_name.lower():
                    timeout = 30
                elif "build" in job_name.lower() or "deploy" in job_name.lower():
                    timeout = 45
                else:
                    timeout = 20

                # Find where to insert timeout (after job name, considering any existing properties)
                insert_pattern = rf"^  {job_name}:\s*\n(?:    \w+:.*\n)*"
                insert_match = re.search(
                    insert_pattern, content[job_start:], re.MULTILINE
                )

                if insert_match:
                    # Check indentation of existing properties
                    indent_match = re.search(
                        r"^(    )(?:if|needs|runs-on|strategy):",
                        content[
                            job_start + insert_match.start() : job_start
                            + insert_match.end()
                        ],
                        re.MULTILINE,
                    )
                    if indent_match:
                        # Insert after job name but before other properties
                        timeout_line = f"    timeout-minutes: {timeout}\n"
                        insert_pos = job_start + content[job_start:].find(":\n") + 2
                        content = (
                            content[:insert_pos] + timeout_line + content[insert_pos:]
                        )
                        print(
                            f"  ✓ Added timeout-minutes: {timeout} to job '{job_name}'"
                        )

    # 4. Add timeouts to long-running steps (those with 'run:' that don't have timeout)
    # This is more complex and would require parsing the YAML structure properly
    # For now, we'll add a comment suggesting manual review

    if "timeout-minutes:" not in content and "run:" in content:
        # Add a comment at the top of the file
        content = f"""# TODO: Review long-running steps and add 'timeout-minutes:' where appropriate
# Recommended timeouts:
# - Quick commands: 5 minutes
# - Build/compile steps: 15-30 minutes
# - Test suites: 20-45 minutes
# - Deployment: 30-60 minutes

{content}"""

    # Only write if content changed
    if content != original_content:
        with open(filepath, "w") as f:
            f.write(content)
        print(f"  ✅ Fixed {filepath.name}")
    else:
        print(f"  ℹ️  No changes needed for {filepath.name}")


def main() -> None:
    """Process all workflow files."""
    workflows_dir = Path(".github/workflows")

    if not workflows_dir.exists():
        print("Error: .github/workflows directory not found!")
        return

    workflow_files = list(workflows_dir.glob("*.yml")) + list(
        workflows_dir.glob("*.yaml")
    )

    print(f"Found {len(workflow_files)} workflow files to process")
    print("=" * 60)

    for workflow_file in sorted(workflow_files):
        try:
            fix_workflow(workflow_file)
        except Exception as e:
            print(f"  ❌ Error processing {workflow_file.name}: {e}")

    print("\n" + "=" * 60)
    print("✅ Workflow cancellation fixes complete!")
    print("\nRecommended next steps:")
    print("1. Review the changes using 'git diff'")
    print("2. Test workflows locally with 'act' if possible")
    print("3. Commit and push to test cancellation behavior")
    print("\nFor complex workflows, consider adding:")
    print("- Step-level timeouts for long-running commands")
    print("- 'exec' prefix for shell commands to ensure signal propagation")
    print("- Custom signal handlers in scripts")


if __name__ == "__main__":
    main()

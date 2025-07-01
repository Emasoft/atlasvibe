#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Smart test detection based on changed files and environment
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import List, Set, Dict, Tuple

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE FILE:
# - Initial creation of smart test detection system
# - Detects which tests to run based on changed files
# - Supports different test strategies for local/remote
# - Integrates with git to find changes
#


class TestDetector:
    """Detects which tests should run based on changes and environment."""

    def __init__(self):
        self.root = Path(__file__).parent
        self.environment = self._detect_environment()
        self.changed_files = self._get_changed_files()

    def _detect_environment(self) -> str:
        """Detect current environment."""
        if os.environ.get("CI") == "true" or os.environ.get("GITHUB_ACTIONS") == "true":
            return "remote"
        elif os.environ.get("DOCKER_HOST") or os.path.exists("/.dockerenv"):
            return "docker"
        else:
            return "local"

    def _get_changed_files(self) -> Set[Path]:
        """Get list of changed files from git."""
        try:
            # Get files changed in last commit
            result = subprocess.run(
                ["git", "diff", "--name-only", "HEAD~1..HEAD"],
                capture_output=True,
                text=True,
                check=True,
            )
            files = {self.root / f.strip() for f in result.stdout.strip().split("\n") if f}

            # Also get uncommitted changes
            result = subprocess.run(
                ["git", "diff", "--name-only"],
                capture_output=True,
                text=True,
                check=True,
            )
            files.update(self.root / f.strip() for f in result.stdout.strip().split("\n") if f)

            return files
        except subprocess.CalledProcessError:
            # If git fails, assume all files changed
            return set()

    def _get_test_categories(self) -> Dict[str, List[str]]:
        """Determine which test categories to run."""
        categories = {
            "python": [],
            "javascript": [],
            "docker": [],
            "ui": [],
            "integration": [],
        }

        # If no changes detected, run all tests
        if not self.changed_files:
            return {
                "python": ["all"],
                "javascript": ["all"],
                "docker": ["all"] if self.environment != "remote" else [],
                "ui": ["all"] if self.environment == "local" else [],
                "integration": ["all"] if self.environment != "remote" else [],
            }

        # Analyze changed files
        for file in self.changed_files:
            if file.suffix == ".py":
                if "blocks" in file.parts:
                    categories["python"].append("blocks")
                elif "captain" in file.parts:
                    categories["python"].append("backend")
                elif "test" in file.name:
                    categories["python"].append("tests")

            elif file.suffix in [".ts", ".tsx", ".js", ".jsx"]:
                if "src/renderer" in str(file):
                    categories["javascript"].append("frontend")
                    categories["ui"].append("electron")
                elif "src/main" in str(file):
                    categories["javascript"].append("electron")

            elif "docker" in file.name.lower() or "Dockerfile" in file.name:
                categories["docker"].append("build")

            elif file.name in ["package.json", "pnpm-lock.yaml"]:
                categories["javascript"].append("deps")

            elif file.name in ["pyproject.toml", "uv.lock"]:
                categories["python"].append("deps")

        # Remove duplicates
        for cat in categories:
            categories[cat] = list(set(categories[cat]))

        return categories

    def get_test_commands(self) -> List[Tuple[str, str]]:
        """Get list of test commands to run."""
        categories = self._get_test_categories()
        commands = []

        # Python tests
        if categories["python"]:
            if "all" in categories["python"]:
                commands.append(("Python Tests", "uv run pytest -v ."))
            elif "blocks" in categories["python"]:
                commands.append(("Block Tests", "uv run pytest -v blocks/"))
            elif "backend" in categories["python"]:
                commands.append(("Backend Tests", "uv run pytest -v captain/"))

        # JavaScript tests
        if categories["javascript"]:
            commands.append(("JavaScript Tests", "pnpm test"))
            if "frontend" in categories["javascript"] or "electron" in categories["javascript"]:
                commands.append(("Lint Check", "pnpm run lint"))

        # Docker tests
        if categories["docker"] and self.environment != "remote":
            commands.append(("Docker Tests", "./test-docker-comprehensive.sh remote"))

        # UI tests
        if categories["ui"] and self.environment == "local":
            commands.append(
                (
                    "UI Tests",
                    "pnpm exec playwright test playwright-test/ui-docker-tests.spec.ts",
                )
            )

        # Integration tests
        if categories["integration"] and self.environment != "remote":
            commands.append(("Integration Tests", "./test-docker-comprehensive.sh integration"))

        return commands

    def generate_test_plan(self) -> Dict[str, any]:
        """Generate a test execution plan."""
        return {
            "environment": self.environment,
            "changed_files": len(self.changed_files),
            "test_commands": self.get_test_commands(),
            "parallel": self.environment == "local",
            "estimated_time": self._estimate_time(),
        }

    def _estimate_time(self) -> int:
        """Estimate test execution time in seconds."""
        commands = self.get_test_commands()
        base_times = {
            "Python Tests": 120,
            "Block Tests": 60,
            "Backend Tests": 40,
            "JavaScript Tests": 30,
            "Lint Check": 10,
            "Docker Tests": 300,
            "UI Tests": 180,
            "Integration Tests": 240,
        }

        total = sum(base_times.get(cmd[0], 60) for cmd in commands)

        # Adjust for environment
        if self.environment == "remote":
            total *= 0.8  # CI is usually faster
        elif self.environment == "docker":
            total *= 1.2  # Docker adds overhead

        return int(total)


def main():
    """Main entry point."""
    detector = TestDetector()
    plan = detector.generate_test_plan()

    print("🔍 Test Detection Results")
    print("========================")
    print(f"Environment: {plan['environment']}")
    print(f"Changed files: {plan['changed_files']}")
    print(f"Estimated time: {plan['estimated_time']}s")
    print("\nTests to run:")

    for name, cmd in plan["test_commands"]:
        print(f"  • {name}: {cmd}")

    # Output JSON for automation
    if "--json" in sys.argv:
        print("\n" + json.dumps(plan, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())

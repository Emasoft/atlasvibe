#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Docker test runner for AtlasVibe
Runs Playwright tests and formats results in a nice table
"""

import subprocess
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any


class TestResult:
    """Represents a single test result"""

    def __init__(self, name: str, suite: str, status: str, duration: float, error: str = ""):
        self.name = name
        self.suite = suite
        self.status = status
        self.duration = duration
        self.error = error
        self.description = self._extract_description(name)

    def _extract_description(self, name: str) -> str:
        """Extract a readable description from test name"""
        # Convert test names like "test_app_launches_successfully" to "App launches successfully"
        if name.startswith("test_"):
            name = name[5:]
        # Handle test names with "should" in them
        if "should" in name.lower():
            return name
        return name.replace("_", " ").capitalize()


class TestReporter:
    """Formats and displays test results in a nice table"""

    def __init__(self):
        self.results: List[TestResult] = []
        self.start_time = datetime.now()

    def run_tests(self) -> int:
        """Run Playwright tests and collect results"""
        print("\n🚀 Starting AtlasVibe Docker Tests...")
        print(f"⏰ Start time: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)

        # Ensure test results directory exists
        Path("/app/test-results").mkdir(exist_ok=True)

        # Run Playwright tests with Docker config
        # Run headless check and API tests only in Docker
        cmd = ["pnpm", "exec", "playwright", "test", "--config=playwright.config.docker.ts", "00_headless_check.spec.ts", "00_api_smoke.spec.ts"]

        print("\n📋 Running Playwright tests...")
        process = subprocess.run(cmd, capture_output=True, text=True)

        # Try to parse JSON results
        results_file = Path("/app/test-results/results.json")
        if results_file.exists():
            try:
                with open(results_file, "r") as f:
                    test_data = json.load(f)
                self._parse_results(test_data)
            except json.JSONDecodeError:
                print("❌ Failed to parse test results JSON")
                # Fallback to parsing stdout
                self._parse_stdout(process.stdout)
        else:
            # Fallback to parsing stdout
            self._parse_stdout(process.stdout)

        # Display results
        self._display_results()

        return process.returncode

    def _parse_results(self, data: Dict[str, Any]) -> None:
        """Parse JSON test results"""
        # Playwright JSON reporter format
        if "suites" in data:
            for suite in data["suites"]:
                self._parse_suite(suite)
        elif "config" in data and "suites" in data.get("config", {}):
            # Alternative format
            for suite in data["config"]["suites"]:
                self._parse_suite(suite)

    def _parse_suite(self, suite: Dict[str, Any], parent_title: str = "") -> None:
        """Recursively parse test suites"""
        suite_name = suite.get("title", "Unknown Suite")
        if parent_title:
            suite_name = f"{parent_title} > {suite_name}"

        # Parse specs in this suite
        for spec in suite.get("specs", []):
            spec_title = spec.get("title", "")
            for test in spec.get("tests", []):
                name = test.get("title", "Unknown Test")
                if spec_title and spec_title != name:
                    name = f"{spec_title}: {name}"

                status = "PASSED"
                duration = 0
                error = ""

                # Check test results
                results = test.get("results", [])
                if results:
                    result = results[0]  # Take first result
                    status_str = result.get("status", "passed").lower()
                    if status_str == "passed":
                        status = "PASSED"
                    elif status_str == "failed":
                        status = "FAILED"
                    elif status_str == "skipped":
                        status = "SKIPPED"

                    duration = result.get("duration", 0) / 1000  # Convert to seconds

                    if result.get("error"):
                        error = result["error"].get("message", "")

                self.results.append(TestResult(name, suite_name, status, duration, error))

        # Recursively parse sub-suites
        for sub_suite in suite.get("suites", []):
            self._parse_suite(sub_suite, suite_name)

    def _parse_stdout(self, stdout: str) -> None:
        """Fallback parser for stdout output"""
        lines = stdout.split("\n")
        current_suite = "Default"

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Look for test results patterns
            if "✓" in line or "✔" in line:
                # Passed test
                test_name = line.split("✓")[-1].strip() if "✓" in line else line.split("✔")[-1].strip()
                if test_name:
                    self.results.append(TestResult(test_name, current_suite, "PASSED", 0.0))
            elif "✗" in line or "✘" in line or "×" in line:
                # Failed test
                test_name = line.split("✗")[-1].strip() if "✗" in line else line.split("✘")[-1].strip()
                if not test_name and "×" in line:
                    test_name = line.split("×")[-1].strip()
                if test_name:
                    self.results.append(TestResult(test_name, current_suite, "FAILED", 0.0))
            elif "●" in line or "○" in line:
                # Skipped test
                test_name = line.split("●")[-1].strip() if "●" in line else line.split("○")[-1].strip()
                if test_name:
                    self.results.append(TestResult(test_name, current_suite, "SKIPPED", 0.0))

    def _display_results(self) -> None:
        """Display test results in a formatted table"""
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()

        # Count results
        total = len(self.results)
        passed = sum(1 for r in self.results if r.status == "PASSED")
        failed = sum(1 for r in self.results if r.status == "FAILED")
        skipped = sum(1 for r in self.results if r.status == "SKIPPED")

        # Display summary
        print("\n" + "=" * 80)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 80)
        print(f"Total Tests: {total}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"⏭️  Skipped: {skipped}")
        print(f"⏱️  Duration: {duration:.2f}s")
        print("=" * 80)

        # Display detailed table
        if self.results:
            print("\n📋 DETAILED TEST RESULTS")
            print("=" * 120)
            print(f"{'Status':<10} {'Suite':<25} {'Test Name':<40} {'Description':<35} {'Duration':<10}")
            print("=" * 120)

            for result in self.results:
                status_emoji = {"PASSED": "✅", "FAILED": "❌", "SKIPPED": "⏭️"}.get(result.status, "❓")

                status_str = f"{status_emoji} {result.status:<7}"
                suite_str = result.suite[:23] + ".." if len(result.suite) > 25 else result.suite
                name_str = result.name[:38] + ".." if len(result.name) > 40 else result.name
                desc_str = result.description[:33] + ".." if len(result.description) > 35 else result.description
                duration_str = f"{result.duration:.3f}s"

                print(f"{status_str} {suite_str:<25} {name_str:<40} {desc_str:<35} {duration_str:<10}")

                if result.status == "FAILED" and result.error:
                    print(f"{'':>10} Error: {result.error[:100]}...")

            print("=" * 120)

        # Display test output files
        print("\n📁 Test Artifacts:")
        test_results_dir = Path("/app/test-results")
        if test_results_dir.exists():
            for file in test_results_dir.iterdir():
                print(f"  - {file.name}")

        # Overall result
        print("\n" + "=" * 80)
        if failed == 0:
            print("🎉 ALL TESTS PASSED! 🎉")
        else:
            print(f"😞 {failed} TESTS FAILED")
        print("=" * 80)


def main():
    """Main entry point"""
    reporter = TestReporter()
    exit_code = reporter.run_tests()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

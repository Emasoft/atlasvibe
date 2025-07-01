#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Local test runner for AtlasVibe
Runs Playwright tests locally and formats results in a nice table
"""

import subprocess
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import time
import signal


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
        self.server_process: Optional[subprocess.Popen] = None

    def start_services(self) -> bool:
        """Start the backend and frontend services"""
        print("\n🚀 Starting AtlasVibe services...")

        # Start the services using pnpm
        try:
            self.server_process = subprocess.Popen(
                ["pnpm", "run", "start-project:ci"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            print("⏳ Waiting for services to be ready...")
            # Wait for services to start (checking if ports are open would be better)
            for i in range(30):
                time.sleep(1)
                print(".", end="", flush=True)
            print("\n✅ Services should be ready!")

            return True

        except Exception as e:
            print(f"❌ Failed to start services: {e}")
            return False

    def stop_services(self):
        """Stop the services"""
        if self.server_process:
            print("\n🛑 Stopping services...")
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.server_process.kill()
            print("✅ Services stopped")

    def ensure_playwright_browsers(self) -> bool:
        """Ensure Playwright browsers are installed"""
        print("\n🌐 Checking Playwright browsers...")

        # Check if browsers need to be installed
        check_cmd = ["pnpm", "exec", "playwright", "install", "--dry-run"]
        check_result = subprocess.run(check_cmd, capture_output=True, text=True)

        if "already downloaded" not in check_result.stdout and "already installed" not in check_result.stdout:
            print("📥 Installing Playwright browsers...")
            install_cmd = ["pnpm", "exec", "playwright", "install", "chromium"]
            install_result = subprocess.run(install_cmd)
            if install_result.returncode != 0:
                print("❌ Failed to install Playwright browsers")
                return False
            print("✅ Playwright browsers installed")
        else:
            print("✅ Playwright browsers already installed")

        return True

    def run_tests(self) -> int:
        """Run Playwright tests and collect results"""
        print("\n🧪 Starting AtlasVibe Local Tests...")
        print(f"⏰ Start time: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)

        # Ensure Playwright browsers are installed
        if not self.ensure_playwright_browsers():
            return 1

        # Ensure test results directory exists
        Path("test-results").mkdir(exist_ok=True)

        # Run API smoke tests that don't require browser
        cmd = [
            "pnpm",
            "exec",
            "playwright",
            "test",
            "00_api_smoke.spec.ts",
            "--reporter=json",
        ]

        print("\n📋 Running Playwright tests...")
        process = subprocess.run(cmd, capture_output=True, text=True)

        # Save output for debugging
        with open("test-results/playwright-output.txt", "w") as f:
            f.write("STDOUT:\n")
            f.write(process.stdout)
            f.write("\n\nSTDERR:\n")
            f.write(process.stderr)

        # Try to parse JSON from stdout
        try:
            # Playwright outputs JSON to stdout when using json reporter
            json_output = process.stdout.strip()
            if json_output:
                test_data = json.loads(json_output)
                self._parse_results(test_data)
        except json.JSONDecodeError:
            print("⚠️  Could not parse JSON output, falling back to stdout parsing")
            self._parse_stdout(process.stdout + "\n" + process.stderr)

        # Display results
        self._display_results()

        return process.returncode

    def _parse_results(self, data: Dict[str, Any]) -> None:
        """Parse JSON test results"""
        # Playwright JSON reporter format
        if "suites" in data:
            for suite in data["suites"]:
                self._parse_suite(suite)

    def _parse_suite(self, suite: Dict[str, Any], parent_title: str = "") -> None:
        """Recursively parse test suites"""
        suite_name = suite.get("title", "") or suite.get("file", "Unknown Suite")
        if parent_title:
            suite_name = f"{parent_title} > {suite_name}"

        # Parse specs in this suite
        for spec in suite.get("specs", []):
            test_name = spec.get("title", "Unknown Test")

            # Parse test cases
            for test in spec.get("tests", []):
                status = "PASSED"
                duration = 0
                error = ""

                # Check test status
                test_status = test.get("status", "")
                if test_status == "skipped":
                    status = "SKIPPED"

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

                self.results.append(TestResult(test_name, suite_name, status, duration, error))

        # Recursively parse sub-suites
        for sub_suite in suite.get("suites", []):
            self._parse_suite(sub_suite, suite_name)

    def _parse_stdout(self, output: str) -> None:
        """Fallback parser for stdout/stderr output"""
        lines = output.split("\n")
        current_suite = "Smoke Tests"

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Look for test results patterns
            if "✓" in line or "✔" in line or "ok" in line.lower():
                # Passed test
                parts = line.split("✓") if "✓" in line else line.split("✔")
                if len(parts) > 1:
                    test_name = parts[-1].strip()
                else:
                    test_name = line

                if test_name and not test_name.startswith("["):
                    self.results.append(TestResult(test_name, current_suite, "PASSED", 0.0))
            elif "✗" in line or "✘" in line or "×" in line or "fail" in line.lower():
                # Failed test
                parts = line.split("✗") if "✗" in line else line.split("✘")
                if len(parts) > 1:
                    test_name = parts[-1].strip()
                else:
                    test_name = line

                if test_name and not test_name.startswith("["):
                    self.results.append(TestResult(test_name, current_suite, "FAILED", 0.0))
            elif "●" in line or "○" in line or "skip" in line.lower():
                # Skipped test
                parts = line.split("●") if "●" in line else line.split("○")
                if len(parts) > 1:
                    test_name = parts[-1].strip()
                else:
                    test_name = line

                if test_name and not test_name.startswith("["):
                    self.results.append(TestResult(test_name, current_suite, "SKIPPED", 0.0))
            elif "describe" in line.lower() or "suite" in line.lower():
                # New test suite
                if ":" in line:
                    current_suite = line.split(":", 1)[1].strip()
                elif "describe" in line.lower():
                    current_suite = line.replace("describe", "").strip()

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
        test_results_dir = Path("test-results")
        if test_results_dir.exists():
            for file in test_results_dir.iterdir():
                print(f"  - {file.name}")

        # Overall result
        print("\n" + "=" * 80)
        if failed == 0 and total > 0:
            print("🎉 ALL TESTS PASSED! 🎉")
        elif total == 0:
            print("⚠️  NO TESTS WERE RUN")
        else:
            print(f"😞 {failed} TESTS FAILED")
        print("=" * 80)


def main():
    """Main entry point"""
    reporter = TestReporter()

    # Handle SIGINT gracefully
    def signal_handler(sig, frame):
        print("\n\n⚠️  Interrupted! Cleaning up...")
        reporter.stop_services()
        sys.exit(1)

    signal.signal(signal.SIGINT, signal_handler)

    try:
        # Start services
        if not reporter.start_services():
            sys.exit(1)

        # Run tests
        exit_code = reporter.run_tests()

    finally:
        # Stop services
        reporter.stop_services()

    sys.exit(exit_code)


if __name__ == "__main__":
    main()

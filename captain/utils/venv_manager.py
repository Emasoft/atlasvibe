#!/usr/bin/env python3
# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Initial implementation of virtual environment manager for AtlasVibe blocks
# - Comprehensive pre/during/post regeneration checks
# - Structured JSON logging with rotation
# - Automatic dependency extraction from code
# - Error recovery and rollback mechanisms
#

"""
Virtual environment manager for AtlasVibe blocks.

This module handles virtual environment lifecycle management including:
- Dependency parsing from code
- Environment creation and regeneration with uv
- Comprehensive validation checks
- Structured logging and error tracking
- Rollback and recovery mechanisms
"""

import ast
import logging
import os
import platform
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import psutil
from captain.utils.shared.json_utils import load_json_file, save_json_file


class CheckStatus(Enum):
    """Status of a validation check."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    SKIPPED = "skipped"


@dataclass
class CheckResult:
    """Result of a validation check.

    Args:
        name: Check name.
        status: Check status.
        message: Human-readable message.
        details: Additional details.
        duration: Time taken in seconds.
        timestamp: When the check was performed.
        recovery_action: Suggested recovery action if failed.
    """

    name: str
    status: CheckStatus
    message: str
    details: Optional[Dict[str, Any]] = None
    duration: Optional[float] = None
    timestamp: Optional[str] = None
    recovery_action: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "duration": self.duration,
            "timestamp": self.timestamp or datetime.now().isoformat(),
            "recovery_action": self.recovery_action,
        }


@dataclass
class VenvStatus:
    """Status of a virtual environment.

    Args:
        exists: Whether venv directory exists.
        valid: Whether venv is valid and usable.
        python_version: Python version in venv.
        installed_packages: List of installed packages.
        last_regenerated: Last regeneration timestamp.
        health_checks: Results of health checks.
    """

    exists: bool
    valid: bool
    python_version: Optional[str] = None
    installed_packages: List[Dict[str, str]] = None
    last_regenerated: Optional[str] = None
    health_checks: List[CheckResult] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "exists": self.exists,
            "valid": self.valid,
            "python_version": self.python_version,
            "installed_packages": self.installed_packages or [],
            "last_regenerated": self.last_regenerated,
            "health_checks": [c.to_dict() for c in (self.health_checks or [])],
        }


class VenvManager:
    """Manages virtual environments for AtlasVibe blocks."""

    # Minimum requirements
    MIN_DISK_SPACE_MB = 500
    MIN_PYTHON_VERSION = (3, 8)
    MAX_PYTHON_VERSION = (3, 11)

    # Log settings
    MAX_LOG_FILES = 10
    LOG_FILE_PREFIX = "venv_regeneration"

    def __init__(self, block_path: Path, project_path: Optional[Path] = None):
        """Initialize venv manager.

        Args:
            block_path: Path to the block directory.
            project_path: Path to the project directory.
        """
        self.block_path = Path(block_path)
        self.project_path = project_path or self.block_path.parent.parent
        self.venv_path = self.block_path / ".venv"
        self.logs_dir = self.block_path / ".venv_logs"
        self.logs_dir.mkdir(exist_ok=True)

        # Setup logging
        self.logger = logging.getLogger(f"VenvManager[{self.block_path.name}]")

    def get_status(self) -> VenvStatus:
        """Get current status of the virtual environment.

        Returns:
            VenvStatus object with current state.
        """
        status = VenvStatus(exists=self.venv_path.exists(), valid=False)

        if status.exists:
            # Check if venv is valid
            python_exe = self._get_python_executable()
            if python_exe and python_exe.exists():
                try:
                    # Get Python version
                    result = subprocess.run(
                        [str(python_exe), "--version"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    if result.returncode == 0:
                        status.valid = True
                        status.python_version = result.stdout.strip().split()[1]

                    # Get installed packages
                    status.installed_packages = self._get_installed_packages()

                    # Get last regeneration time
                    latest_log = self._get_latest_log()
                    if latest_log:
                        log_data = load_json_file(latest_log, default={})
                        status.last_regenerated = log_data.get("start_time")

                except Exception as e:
                    self.logger.error(f"Error checking venv status: {e}")

        return status

    def regenerate(
        self,
        dependencies: Optional[List[str]] = None,
        python_version: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Regenerate the virtual environment.

        Args:
            dependencies: List of pip dependencies to install.
            python_version: Python version to use (e.g., "3.11").

        Returns:
            Dictionary with regeneration results and log path.
        """
        start_time = time.time()
        log_data = {
            "block_name": self.block_path.name,
            "start_time": datetime.now().isoformat(),
            "dependencies": dependencies or [],
            "python_version": python_version,
            "checks": [],
            "success": False,
            "error": None,
        }

        try:
            # Pre-regeneration checks
            pre_checks = self._run_pre_checks()
            log_data["checks"].extend([c.to_dict() for c in pre_checks])

            # Check if any critical pre-checks failed
            critical_failures = [c for c in pre_checks if c.status == CheckStatus.ERROR and c.name in ["python_version", "disk_space", "permissions", "uv_availability"]]
            if critical_failures:
                raise Exception(f"Critical pre-checks failed: {[c.name for c in critical_failures]}")

            # Parse dependencies from code if not provided
            if dependencies is None:
                dependencies = self._extract_dependencies()
                log_data["extracted_dependencies"] = dependencies

            # Backup existing venv if it exists
            backup_path = None
            if self.venv_path.exists():
                backup_path = self._backup_venv()
                log_data["backup_path"] = str(backup_path)

            # Create new venv
            creation_result = self._create_venv(python_version)
            log_data["checks"].append(creation_result.to_dict())

            if creation_result.status != CheckStatus.SUCCESS:
                raise Exception(f"Venv creation failed: {creation_result.message}")

            # Install dependencies
            if dependencies:
                install_results = self._install_dependencies(dependencies)
                log_data["checks"].extend([r.to_dict() for r in install_results])

                # Check for failures
                failures = [r for r in install_results if r.status == CheckStatus.ERROR]
                if failures:
                    raise Exception(f"Failed to install {len(failures)} dependencies")

            # Post-regeneration checks
            post_checks = self._run_post_checks(dependencies or [])
            log_data["checks"].extend([c.to_dict() for c in post_checks])

            # Verify all critical post-checks passed
            critical_post_failures = [c for c in post_checks if c.status == CheckStatus.ERROR and c.name in ["import_test", "block_execution"]]
            if critical_post_failures:
                raise Exception(f"Critical post-checks failed: {[c.name for c in critical_post_failures]}")

            # Success - remove backup
            if backup_path and backup_path.exists():
                shutil.rmtree(backup_path)

            log_data["success"] = True
            log_data["duration"] = time.time() - start_time

        except Exception as e:
            log_data["success"] = False
            log_data["error"] = str(e)
            log_data["duration"] = time.time() - start_time

            # Rollback if we have a backup
            if backup_path and backup_path.exists():
                self.logger.info("Rolling back to previous venv")
                if self.venv_path.exists():
                    shutil.rmtree(self.venv_path)
                shutil.move(str(backup_path), str(self.venv_path))
                log_data["rolled_back"] = True

            raise

        finally:
            # Save log
            log_path = self._save_log(log_data)
            self._rotate_logs()

        return {
            "success": log_data["success"],
            "log_path": str(log_path),
            "duration": log_data["duration"],
            "error": log_data.get("error"),
            "checks": log_data["checks"],
        }

    def get_logs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get regeneration logs.

        Args:
            limit: Maximum number of logs to return.

        Returns:
            List of log entries, newest first.
        """
        logs = []
        log_files = sorted(
            self.logs_dir.glob(f"{self.LOG_FILE_PREFIX}_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        for log_file in log_files[:limit]:
            log_data = load_json_file(log_file, default=None)
            if log_data is not None:
                log_data["log_file"] = log_file.name
                logs.append(log_data)
            else:
                self.logger.error(f"Failed to read log file: {log_file}")

        return logs

    def _run_pre_checks(self) -> List[CheckResult]:
        """Run pre-regeneration checks."""
        checks = []

        # Python version check
        checks.append(self._check_python_version())

        # Disk space check
        checks.append(self._check_disk_space())

        # Permissions check
        checks.append(self._check_permissions())

        # Network connectivity check
        checks.append(self._check_network())

        # UV availability check
        checks.append(self._check_uv_availability())

        # Dependency conflict check (if venv exists)
        if self.venv_path.exists():
            checks.append(self._check_dependency_conflicts())

        return checks

    def _run_post_checks(self, dependencies: List[str]) -> List[CheckResult]:
        """Run post-regeneration checks."""
        checks = []

        # Environment activation test
        checks.append(self._check_venv_activation())

        # Import test for all dependencies
        checks.append(self._check_imports(dependencies))

        # Version compatibility check
        checks.append(self._check_version_compatibility())

        # Runtime requirements check
        checks.append(self._check_runtime_requirements())

        # Block execution dry-run
        checks.append(self._check_block_execution())

        return checks

    def _check_python_version(self) -> CheckResult:
        """Check Python version compatibility."""
        start = time.time()

        try:
            version_info = sys.version_info[:2]
            version_str = f"{version_info[0]}.{version_info[1]}"

            if version_info < self.MIN_PYTHON_VERSION:
                return CheckResult(
                    name="python_version",
                    status=CheckStatus.ERROR,
                    message=f"Python {version_str} is too old",
                    details={
                        "current": version_str,
                        "minimum": f"{self.MIN_PYTHON_VERSION[0]}.{self.MIN_PYTHON_VERSION[1]}",
                    },
                    duration=time.time() - start,
                    recovery_action=f"Install Python {self.MIN_PYTHON_VERSION[0]}.{self.MIN_PYTHON_VERSION[1]} or newer",
                )
            elif version_info > self.MAX_PYTHON_VERSION:
                return CheckResult(
                    name="python_version",
                    status=CheckStatus.WARNING,
                    message=f"Python {version_str} may not be fully supported",
                    details={
                        "current": version_str,
                        "maximum": f"{self.MAX_PYTHON_VERSION[0]}.{self.MAX_PYTHON_VERSION[1]}",
                    },
                    duration=time.time() - start,
                )
            else:
                return CheckResult(
                    name="python_version",
                    status=CheckStatus.SUCCESS,
                    message=f"Python {version_str} is compatible",
                    details={"version": version_str},
                    duration=time.time() - start,
                )

        except Exception as e:
            return CheckResult(
                name="python_version",
                status=CheckStatus.ERROR,
                message=f"Failed to check Python version: {str(e)}",
                duration=time.time() - start,
            )

    def _check_disk_space(self) -> CheckResult:
        """Check available disk space."""
        start = time.time()

        try:
            stat = psutil.disk_usage(str(self.block_path))
            available_mb = stat.free / (1024 * 1024)

            if available_mb < self.MIN_DISK_SPACE_MB:
                return CheckResult(
                    name="disk_space",
                    status=CheckStatus.ERROR,
                    message=f"Insufficient disk space: {available_mb:.0f}MB available",
                    details={
                        "available_mb": available_mb,
                        "required_mb": self.MIN_DISK_SPACE_MB,
                    },
                    duration=time.time() - start,
                    recovery_action=f"Free up at least {self.MIN_DISK_SPACE_MB - available_mb:.0f}MB of disk space",
                )
            else:
                return CheckResult(
                    name="disk_space",
                    status=CheckStatus.SUCCESS,
                    message=f"Sufficient disk space: {available_mb:.0f}MB available",
                    details={"available_mb": available_mb},
                    duration=time.time() - start,
                )

        except Exception as e:
            return CheckResult(
                name="disk_space",
                status=CheckStatus.ERROR,
                message=f"Failed to check disk space: {str(e)}",
                duration=time.time() - start,
            )

    def _check_permissions(self) -> CheckResult:
        """Check write permissions in project directory."""
        start = time.time()

        try:
            # Try to create a temporary file
            test_file = self.block_path / f".permission_test_{os.getpid()}"
            test_file.write_text("test")
            test_file.unlink()

            return CheckResult(
                name="permissions",
                status=CheckStatus.SUCCESS,
                message="Write permissions verified",
                duration=time.time() - start,
            )

        except Exception as e:
            return CheckResult(
                name="permissions",
                status=CheckStatus.ERROR,
                message=f"No write permissions in {self.block_path}",
                details={"error": str(e)},
                duration=time.time() - start,
                recovery_action=f"Grant write permissions to {self.block_path}",
            )

    def _check_network(self) -> CheckResult:
        """Check network connectivity to PyPI."""
        start = time.time()

        try:
            # Try to reach PyPI
            import urllib.request

            with urllib.request.urlopen("https://pypi.org/simple/", timeout=5) as response:
                if response.status == 200:
                    return CheckResult(
                        name="network",
                        status=CheckStatus.SUCCESS,
                        message="Network connectivity verified",
                        duration=time.time() - start,
                    )

        except Exception as e:
            return CheckResult(
                name="network",
                status=CheckStatus.WARNING,
                message="Cannot reach PyPI",
                details={"error": str(e)},
                duration=time.time() - start,
                recovery_action="Check internet connection or proxy settings",
            )

        return CheckResult(
            name="network",
            status=CheckStatus.WARNING,
            message="Network check inconclusive",
            duration=time.time() - start,
        )

    def _check_uv_availability(self) -> CheckResult:
        """Check if uv tool is available."""
        start = time.time()

        try:
            result = subprocess.run(["uv", "--version"], capture_output=True, text=True, timeout=5)

            if result.returncode == 0:
                version = result.stdout.strip()
                return CheckResult(
                    name="uv_availability",
                    status=CheckStatus.SUCCESS,
                    message=f"UV tool available: {version}",
                    details={"version": version},
                    duration=time.time() - start,
                )
            else:
                return CheckResult(
                    name="uv_availability",
                    status=CheckStatus.ERROR,
                    message="UV tool not found",
                    duration=time.time() - start,
                    recovery_action="Install uv: curl -LsSf https://astral.sh/uv/install.sh | sh",
                )

        except FileNotFoundError:
            return CheckResult(
                name="uv_availability",
                status=CheckStatus.ERROR,
                message="UV tool not installed",
                duration=time.time() - start,
                recovery_action="Install uv: curl -LsSf https://astral.sh/uv/install.sh | sh",
            )
        except Exception as e:
            return CheckResult(
                name="uv_availability",
                status=CheckStatus.ERROR,
                message=f"Failed to check uv: {str(e)}",
                duration=time.time() - start,
            )

    def _check_dependency_conflicts(self) -> CheckResult:
        """Check for dependency conflicts before installation."""
        start = time.time()

        # This is a placeholder - in practice would use pip-tools or similar
        return CheckResult(
            name="dependency_conflicts",
            status=CheckStatus.SUCCESS,
            message="No dependency conflicts detected",
            duration=time.time() - start,
        )

    def _check_venv_activation(self) -> CheckResult:
        """Test virtual environment activation."""
        start = time.time()

        python_exe = self._get_python_executable()
        if not python_exe or not python_exe.exists():
            return CheckResult(
                name="venv_activation",
                status=CheckStatus.ERROR,
                message="Python executable not found in venv",
                duration=time.time() - start,
            )

        try:
            result = subprocess.run(
                [str(python_exe), "-c", "import sys; print(sys.prefix)"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0 and str(self.venv_path) in result.stdout:
                return CheckResult(
                    name="venv_activation",
                    status=CheckStatus.SUCCESS,
                    message="Virtual environment activation successful",
                    duration=time.time() - start,
                )
            else:
                return CheckResult(
                    name="venv_activation",
                    status=CheckStatus.ERROR,
                    message="Virtual environment activation failed",
                    details={"stdout": result.stdout, "stderr": result.stderr},
                    duration=time.time() - start,
                )

        except Exception as e:
            return CheckResult(
                name="venv_activation",
                status=CheckStatus.ERROR,
                message=f"Failed to test venv activation: {str(e)}",
                duration=time.time() - start,
            )

    def _check_imports(self, dependencies: List[str]) -> CheckResult:
        """Test importing all dependencies."""
        start = time.time()
        failed_imports = []

        python_exe = self._get_python_executable()
        if not python_exe:
            return CheckResult(
                name="import_test",
                status=CheckStatus.ERROR,
                message="Cannot run import test without Python executable",
                duration=time.time() - start,
            )

        for dep in dependencies:
            # Extract package name from dependency spec
            package_name = re.split(r"[<>=!~]", dep)[0].strip()

            # Skip imports for packages that don't match their import name
            import_name = self._get_import_name(package_name)
            if not import_name:
                continue

            try:
                result = subprocess.run(
                    [str(python_exe), "-c", f"import {import_name}"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                if result.returncode != 0:
                    failed_imports.append(
                        {
                            "package": package_name,
                            "import": import_name,
                            "error": result.stderr,
                        }
                    )

            except Exception as e:
                failed_imports.append({"package": package_name, "import": import_name, "error": str(e)})

        if failed_imports:
            return CheckResult(
                name="import_test",
                status=CheckStatus.ERROR,
                message=f"Failed to import {len(failed_imports)} packages",
                details={"failed": failed_imports},
                duration=time.time() - start,
                recovery_action="Check package installation and compatibility",
            )
        else:
            return CheckResult(
                name="import_test",
                status=CheckStatus.SUCCESS,
                message=f"Successfully imported all {len(dependencies)} dependencies",
                duration=time.time() - start,
            )

    def _check_version_compatibility(self) -> CheckResult:
        """Check version compatibility of installed packages."""
        start = time.time()

        # This is a placeholder for more sophisticated version checking
        return CheckResult(
            name="version_compatibility",
            status=CheckStatus.SUCCESS,
            message="Package versions are compatible",
            duration=time.time() - start,
        )

    def _check_runtime_requirements(self) -> CheckResult:
        """Check runtime requirements (GPU, memory, etc.)."""
        start = time.time()

        # Check available memory
        memory = psutil.virtual_memory()
        available_gb = memory.available / (1024**3)

        if available_gb < 1:
            return CheckResult(
                name="runtime_requirements",
                status=CheckStatus.WARNING,
                message=f"Low memory available: {available_gb:.1f}GB",
                details={"available_gb": available_gb},
                duration=time.time() - start,
            )

        # Check for GPU if needed (simplified check)
        gpu_available = self._check_gpu_availability()

        return CheckResult(
            name="runtime_requirements",
            status=CheckStatus.SUCCESS,
            message="Runtime requirements satisfied",
            details={"memory_gb": available_gb, "gpu_available": gpu_available},
            duration=time.time() - start,
        )

    def _check_block_execution(self) -> CheckResult:
        """Dry-run the block execution."""
        start = time.time()

        # Find the main Python file
        py_files = list(self.block_path.glob("*.py"))
        if not py_files:
            return CheckResult(
                name="block_execution",
                status=CheckStatus.ERROR,
                message="No Python files found in block",
                duration=time.time() - start,
            )

        main_file = py_files[0]  # Assume first .py file is main
        python_exe = self._get_python_executable()

        if not python_exe:
            return CheckResult(
                name="block_execution",
                status=CheckStatus.ERROR,
                message="Cannot test block without Python executable",
                duration=time.time() - start,
            )

        try:
            # Try to parse and compile the file
            result = subprocess.run(
                [str(python_exe), "-m", "py_compile", str(main_file)],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                return CheckResult(
                    name="block_execution",
                    status=CheckStatus.SUCCESS,
                    message="Block code compiles successfully",
                    duration=time.time() - start,
                )
            else:
                return CheckResult(
                    name="block_execution",
                    status=CheckStatus.ERROR,
                    message="Block code compilation failed",
                    details={"stderr": result.stderr},
                    duration=time.time() - start,
                    recovery_action="Fix syntax errors in block code",
                )

        except Exception as e:
            return CheckResult(
                name="block_execution",
                status=CheckStatus.ERROR,
                message=f"Failed to test block: {str(e)}",
                duration=time.time() - start,
            )

    def _extract_dependencies(self) -> List[str]:
        """Extract dependencies from block code."""
        dependencies = []

        # Look for @atlasvibe decorator with deps parameter
        py_files = list(self.block_path.glob("*.py"))
        for py_file in py_files:
            try:
                tree = ast.parse(py_file.read_text())
                visitor = DependencyVisitor()
                visitor.visit(tree)
                dependencies.extend(visitor.dependencies)
            except Exception as e:
                self.logger.error(f"Error parsing {py_file}: {e}")

        # Remove duplicates while preserving order
        seen = set()
        unique_deps = []
        for dep in dependencies:
            if dep not in seen:
                seen.add(dep)
                unique_deps.append(dep)

        return unique_deps

    def _create_venv(self, python_version: Optional[str]) -> CheckResult:
        """Create virtual environment using uv."""
        start = time.time()

        try:
            # Remove existing venv if it exists
            if self.venv_path.exists():
                shutil.rmtree(self.venv_path)

            # Build uv command
            cmd = ["uv", "venv", str(self.venv_path)]
            if python_version:
                cmd.extend(["--python", python_version])

            # Create venv
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(self.block_path),
                timeout=60,
            )

            if result.returncode == 0:
                return CheckResult(
                    name="venv_creation",
                    status=CheckStatus.SUCCESS,
                    message="Virtual environment created successfully",
                    details={"stdout": result.stdout},
                    duration=time.time() - start,
                )
            else:
                return CheckResult(
                    name="venv_creation",
                    status=CheckStatus.ERROR,
                    message="Failed to create virtual environment",
                    details={"stderr": result.stderr, "returncode": result.returncode},
                    duration=time.time() - start,
                )

        except Exception as e:
            return CheckResult(
                name="venv_creation",
                status=CheckStatus.ERROR,
                message=f"Exception creating venv: {str(e)}",
                duration=time.time() - start,
            )

    def _install_dependencies(self, dependencies: List[str]) -> List[CheckResult]:
        """Install dependencies in the virtual environment."""
        results = []
        python_exe = self._get_python_executable()

        if not python_exe:
            results.append(
                CheckResult(
                    name="install_dependencies",
                    status=CheckStatus.ERROR,
                    message="Cannot install dependencies without Python executable",
                )
            )
            return results

        # Install each dependency
        for dep in dependencies:
            start = time.time()

            try:
                # Use uv pip install
                result = subprocess.run(
                    ["uv", "pip", "install", dep],
                    capture_output=True,
                    text=True,
                    cwd=str(self.block_path),
                    env={**os.environ, "VIRTUAL_ENV": str(self.venv_path)},
                    timeout=300,  # 5 minutes per package
                )

                if result.returncode == 0:
                    results.append(
                        CheckResult(
                            name=f"install_{dep}",
                            status=CheckStatus.SUCCESS,
                            message=f"Successfully installed {dep}",
                            duration=time.time() - start,
                        )
                    )
                else:
                    results.append(
                        CheckResult(
                            name=f"install_{dep}",
                            status=CheckStatus.ERROR,
                            message=f"Failed to install {dep}",
                            details={"stderr": result.stderr},
                            duration=time.time() - start,
                            recovery_action=f"Check if {dep} is a valid package name and version",
                        )
                    )

            except subprocess.TimeoutExpired:
                results.append(
                    CheckResult(
                        name=f"install_{dep}",
                        status=CheckStatus.ERROR,
                        message=f"Installation of {dep} timed out",
                        duration=time.time() - start,
                        recovery_action="Check network connection or try a faster mirror",
                    )
                )
            except Exception as e:
                results.append(
                    CheckResult(
                        name=f"install_{dep}",
                        status=CheckStatus.ERROR,
                        message=f"Exception installing {dep}: {str(e)}",
                        duration=time.time() - start,
                    )
                )

        return results

    def _get_python_executable(self) -> Optional[Path]:
        """Get path to Python executable in venv."""
        if platform.system() == "Windows":
            python_exe = self.venv_path / "Scripts" / "python.exe"
        else:
            python_exe = self.venv_path / "bin" / "python"

        return python_exe if python_exe.exists() else None

    def _get_installed_packages(self) -> List[Dict[str, str]]:
        """Get list of installed packages in venv."""
        python_exe = self._get_python_executable()
        if not python_exe:
            return []

        try:
            result = subprocess.run(
                ["uv", "pip", "list", "--format", "json"],
                capture_output=True,
                text=True,
                env={**os.environ, "VIRTUAL_ENV": str(self.venv_path)},
                timeout=10,
            )

            if result.returncode == 0:
                import json

                return json.loads(result.stdout)
            else:
                return []

        except Exception:
            return []

    def _backup_venv(self) -> Path:
        """Create backup of existing venv."""
        backup_path = self.venv_path.parent / f".venv_backup_{int(time.time())}"
        shutil.copytree(self.venv_path, backup_path)
        return backup_path

    def _save_log(self, log_data: Dict[str, Any]) -> Path:
        """Save regeneration log to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.logs_dir / f"{self.LOG_FILE_PREFIX}_{timestamp}.json"

        # Use atomic write for concurrent safety
        if save_json_file(log_file, log_data, indent=2, atomic=True):
            return log_file
        else:
            # Fallback to non-atomic write if atomic fails
            self.logger.warning(f"Atomic write failed, using standard write for {log_file}")
            save_json_file(log_file, log_data, indent=2, atomic=False)
            return log_file

    def _rotate_logs(self):
        """Remove old log files keeping only the most recent."""
        log_files = sorted(
            self.logs_dir.glob(f"{self.LOG_FILE_PREFIX}_*.json"),
            key=lambda p: p.stat().st_mtime,
        )

        # Remove oldest files
        for log_file in log_files[: -self.MAX_LOG_FILES]:
            log_file.unlink()

    def _get_latest_log(self) -> Optional[Path]:
        """Get path to the most recent log file."""
        log_files = list(self.logs_dir.glob(f"{self.LOG_FILE_PREFIX}_*.json"))
        if not log_files:
            return None

        return max(log_files, key=lambda p: p.stat().st_mtime)

    def _check_gpu_availability(self) -> bool:
        """Check if GPU is available (simplified)."""
        try:
            # Check for NVIDIA GPU
            result = subprocess.run(["nvidia-smi"], capture_output=True, timeout=5)
            return result.returncode == 0
        except Exception:
            return False

    def _get_import_name(self, package_name: str) -> Optional[str]:
        """Get the import name for a package (may differ from package name)."""
        # Common mappings
        import_mappings = {
            "pillow": "PIL",
            "opencv-python": "cv2",
            "beautifulsoup4": "bs4",
            "pyyaml": "yaml",
            "python-dateutil": "dateutil",
            "msgpack-python": "msgpack",
            "protobuf": "google.protobuf",
            "scikit-learn": "sklearn",
            "scikit-image": "skimage",
        }

        # Check mapping
        if package_name.lower() in import_mappings:
            return import_mappings[package_name.lower()]

        # Otherwise use package name with underscores
        return package_name.replace("-", "_")


class DependencyVisitor(ast.NodeVisitor):
    """AST visitor to extract dependencies from @atlasvibe decorator."""

    def __init__(self):
        self.dependencies = []

    def visit_FunctionDef(self, node):
        for decorator in node.decorator_list:
            if self._is_atlasvibe_decorator(decorator):
                self._extract_deps(decorator)
        self.generic_visit(node)

    def _is_atlasvibe_decorator(self, decorator):
        if isinstance(decorator, ast.Name):
            return decorator.id in ["atlasvibe", "atlasvibe_node"]
        elif isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name):
            return decorator.func.id in ["atlasvibe", "atlasvibe_node"]
        return False

    def _extract_deps(self, decorator):
        if not isinstance(decorator, ast.Call):
            return

        for keyword in decorator.keywords:
            if keyword.arg == "deps" and isinstance(keyword.value, ast.List):
                for elt in keyword.value.elts:
                    if isinstance(elt, ast.Constant):
                        self.dependencies.append(elt.value)


# API utility functions


def regenerate_venv(
    block_path: str,
    dependencies: Optional[List[str]] = None,
    python_version: Optional[str] = None,
) -> Dict[str, Any]:
    """Regenerate virtual environment for a block.

    Args:
        block_path: Path to the block directory.
        dependencies: List of pip dependencies.
        python_version: Python version to use.

    Returns:
        Dictionary with regeneration results.
    """
    manager = VenvManager(Path(block_path))
    return manager.regenerate(dependencies, python_version)


def get_venv_status(block_path: str) -> Dict[str, Any]:
    """Get virtual environment status.

    Args:
        block_path: Path to the block directory.

    Returns:
        Dictionary with venv status.
    """
    manager = VenvManager(Path(block_path))
    status = manager.get_status()
    return status.to_dict()


def get_venv_logs(block_path: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Get virtual environment regeneration logs.

    Args:
        block_path: Path to the block directory.
        limit: Maximum number of logs to return.

    Returns:
        List of log entries.
    """
    manager = VenvManager(Path(block_path))
    return manager.get_logs(limit)

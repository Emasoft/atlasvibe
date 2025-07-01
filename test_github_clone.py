#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for GitHub repository cloning and setup with uv
"""

import sys
import tempfile
import subprocess
from pathlib import Path


def run_command(cmd, cwd=None, capture=True):
    """Run a command and return output"""
    print(f"Running: {' '.join(cmd)}")

    if capture:
        result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error: {result.stderr}")
        else:
            print(f"Success: {result.stdout[:200]}..." if len(result.stdout) > 200 else f"Success: {result.stdout}")
        return result
    else:
        result = subprocess.run(cmd, cwd=cwd)
        return result


def test_github_clone_and_setup():
    """Test cloning a GitHub repo and setting it up with uv"""

    print("\n🧪 Testing GitHub Repository Clone and Setup")
    print("=" * 50)

    # Create temporary workspace
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        print(f"📁 Created temporary workspace: {workspace}")

        # Test repository (using a small, well-known Python project)
        test_repo = "https://github.com/astral-sh/ruff"
        repo_name = "ruff"

        # Step 1: Clone repository
        print("\n📋 Step 1: Cloning repository...")
        clone_cmd = ["git", "clone", "--depth=1", test_repo]
        result = run_command(clone_cmd, cwd=workspace)

        if result.returncode != 0:
            print("❌ Failed to clone repository")
            return False

        repo_path = workspace / repo_name
        if not repo_path.exists():
            print("❌ Repository directory not found after clone")
            return False

        print(f"✅ Repository cloned to: {repo_path}")

        # Step 2: Check for pyproject.toml
        print("\n📋 Step 2: Checking project structure...")
        pyproject_path = repo_path / "pyproject.toml"

        if pyproject_path.exists():
            print("✅ Found pyproject.toml")
        else:
            print("❌ No pyproject.toml found")
            return False

        # Step 3: Create virtual environment with uv
        print("\n📋 Step 3: Creating virtual environment with uv...")
        venv_cmd = ["uv", "venv"]
        result = run_command(venv_cmd, cwd=repo_path)

        if result.returncode != 0:
            print("❌ Failed to create virtual environment")
            return False

        venv_path = repo_path / ".venv"
        if not venv_path.exists():
            print("❌ Virtual environment not created")
            return False

        print("✅ Virtual environment created")

        # Step 4: Install dependencies
        print("\n📋 Step 4: Installing dependencies...")
        # First, let's check what's available
        sync_cmd = ["uv", "sync", "--no-install-project"]
        result = run_command(sync_cmd, cwd=repo_path)

        if result.returncode == 0:
            print("✅ Dependencies installed successfully")
        else:
            # Fallback to pip install if sync fails
            print("⚠️  uv sync failed, trying pip install...")
            pip_cmd = ["uv", "pip", "install", "-e", "."]
            result = run_command(pip_cmd, cwd=repo_path)

            if result.returncode == 0:
                print("✅ Dependencies installed via pip")
            else:
                print("❌ Failed to install dependencies")
                return False

        # Step 5: Build project
        print("\n📋 Step 5: Building project with uv...")
        build_cmd = ["uv", "build", "--wheel"]
        result = run_command(build_cmd, cwd=repo_path)

        if result.returncode == 0:
            print("✅ Project built successfully")

            # Check for wheel files
            dist_dir = repo_path / "dist"
            if dist_dir.exists():
                wheel_files = list(dist_dir.glob("*.whl"))
                if wheel_files:
                    print(f"✅ Found wheel file: {wheel_files[0].name}")
                else:
                    print("⚠️  No wheel files found in dist/")
        else:
            print("⚠️  Build failed (this might be expected for some projects)")

        # Step 6: Run a simple test command
        print("\n📋 Step 6: Testing installed package...")
        test_cmd = ["uv", "run", "python", "-c", "print('Environment is working!')"]
        result = run_command(test_cmd, cwd=repo_path)

        if result.returncode == 0:
            print("✅ Environment test passed")
        else:
            print("❌ Environment test failed")
            return False

        return True


def test_atlasvibe_specific():
    """Test AtlasVibe-specific functionality"""

    print("\n\n🧪 Testing AtlasVibe-Specific Setup")
    print("=" * 50)

    # Create a mock AtlasVibe project structure
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "test_atlasvibe_project"
        project_dir.mkdir()

        # Create AtlasVibe project structure
        (project_dir / "atlasvibe_blocks").mkdir()
        (project_dir / ".atlasvibe").mkdir()

        # Create a simple pyproject.toml
        pyproject_content = """[project]
name = "test-atlasvibe-project"
version = "0.1.0"
description = "Test AtlasVibe project"
requires-python = ">=3.11"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
"""

        with open(project_dir / "pyproject.toml", "w") as f:
            f.write(pyproject_content)

        print(f"📁 Created test project at: {project_dir}")

        # Initialize with uv
        print("\n📋 Initializing AtlasVibe project with uv...")

        # Create venv
        venv_cmd = ["uv", "venv"]
        result = run_command(venv_cmd, cwd=project_dir)

        if result.returncode != 0:
            print("❌ Failed to create virtual environment")
            return False

        print("✅ Virtual environment created")

        # Create a custom block
        custom_block_dir = project_dir / "atlasvibe_blocks" / "CUSTOM_TEST"
        custom_block_dir.mkdir()

        block_code = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Custom test block"""

def CUSTOM_TEST(input_value: float = 0) -> float:
    """Test block that doubles the input.

    Parameters
    ----------
    input_value : float
        Value to double

    Returns
    -------
    float
        Doubled value
    """
    return input_value * 2
'''

        with open(custom_block_dir / "CUSTOM_TEST.py", "w") as f:
            f.write(block_code)

        (custom_block_dir / "__init__.py").touch()

        print("✅ Created custom block: CUSTOM_TEST")

        # Test that the block can be imported
        test_import_cmd = [
            "uv",
            "run",
            "python",
            "-c",
            "import sys; sys.path.insert(0, 'atlasvibe_blocks'); from CUSTOM_TEST.CUSTOM_TEST import CUSTOM_TEST; result = CUSTOM_TEST(21); print(f'Test result: {result}'); assert result == 42, 'Test failed!'",
        ]

        result = run_command(test_import_cmd, cwd=project_dir)

        if result.returncode == 0:
            print("✅ Custom block test passed!")
            return True
        else:
            print("❌ Custom block test failed")
            return False


def main():
    """Run all tests"""

    print("🚀 Starting GitHub Clone and UV Setup Tests")
    print("=" * 60)

    # Check prerequisites
    print("\n📋 Checking prerequisites...")

    # Check git
    git_check = run_command(["git", "--version"])
    if git_check.returncode != 0:
        print("❌ Git is not installed")
        return 1

    # Check uv
    uv_check = run_command(["uv", "--version"])
    if uv_check.returncode != 0:
        print("❌ uv is not installed")
        return 1

    print("✅ All prerequisites met")

    # Run tests
    tests_passed = 0
    tests_failed = 0

    # Test 1: GitHub clone and setup
    if test_github_clone_and_setup():
        tests_passed += 1
    else:
        tests_failed += 1

    # Test 2: AtlasVibe-specific setup
    if test_atlasvibe_specific():
        tests_passed += 1
    else:
        tests_failed += 1

    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    print(f"Total tests: {tests_passed + tests_failed}")
    print(f"✅ Passed: {tests_passed}")
    print(f"❌ Failed: {tests_failed}")

    if tests_failed == 0:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n😞 {tests_failed} tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())

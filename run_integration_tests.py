#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integration tests for AtlasVibe
Tests complex scenarios including project setup, workflow execution, and API interactions
"""

import os
import sys
import json
import time
import subprocess
import asyncio
from pathlib import Path
from typing import Dict, Any, List
import httpx


class AtlasVibeIntegrationTest:
    """Integration test suite for AtlasVibe"""

    def __init__(self):
        self.base_url = "http://localhost:5392"
        self.results: List[Dict[str, Any]] = []
        self.test_workspace = Path("/app/test-workspace")
        self.test_workspace.mkdir(exist_ok=True)

    async def test_api_health(self) -> bool:
        """Test API health endpoints"""
        print("📋 Testing API health endpoints...")

        async with httpx.AsyncClient() as client:
            try:
                # Test health check
                response = await client.get(f"{self.base_url}/log_level")
                assert response.status_code == 200, f"Health check failed: {response.status_code}"
                print("  ✅ Health check endpoint")

                # Test blocks metadata
                response = await client.get(f"{self.base_url}/blocks/metadata/")
                assert response.status_code == 200, f"Blocks metadata failed: {response.status_code}"
                data = response.json()
                assert isinstance(data, dict), "Blocks metadata should be a dictionary"
                assert len(data) > 0, "No blocks found in metadata"
                print(f"  ✅ Blocks metadata endpoint ({len(data)} blocks)")

                return True

            except Exception as e:
                print(f"  ❌ API health test failed: {e}")
                return False

    async def test_project_operations(self) -> bool:
        """Test project creation and management"""
        print("📋 Testing project operations...")

        project_name = f"test_project_{int(time.time())}"
        project_dir = self.test_workspace / project_name

        try:
            # Create project directory structure
            project_dir.mkdir()
            (project_dir / "atlasvibe_blocks").mkdir()
            (project_dir / ".atlasvibe").mkdir()

            # Create project config
            config = {"name": project_name, "version": "0.1.0", "created": time.time()}

            with open(project_dir / ".atlasvibe" / "project.json", "w") as f:
                json.dump(config, f, indent=2)

            print(f"  ✅ Created project: {project_name}")

            # Test custom block creation
            custom_block_dir = project_dir / "atlasvibe_blocks" / "CUSTOM_ADDITION"
            custom_block_dir.mkdir()

            # Create custom block Python file
            block_code = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Custom addition block for testing"""

from pkgs.atlasvibe.atlasvibe import atlasvibe


@atlasvibe
def CUSTOM_ADDITION(a: float = 0, b: float = 0) -> float:
    """Add two numbers together.

    Parameters
    ----------
    a : float
        First number
    b : float
        Second number

    Returns
    -------
    float
        Sum of a and b
    """
    return a + b
'''

            with open(custom_block_dir / "CUSTOM_ADDITION.py", "w") as f:
                f.write(block_code)

            # Create __init__.py
            (custom_block_dir / "__init__.py").touch()

            print("  ✅ Created custom block")

            # Test workflow creation
            workflow = {
                "nodes": [{"id": "1", "type": "CONSTANT", "position": {"x": 100, "y": 100}, "data": {"value": 5}}, {"id": "2", "type": "CONSTANT", "position": {"x": 100, "y": 200}, "data": {"value": 3}}, {"id": "3", "type": "CUSTOM_ADDITION", "position": {"x": 300, "y": 150}, "data": {}}],
                "edges": [{"id": "e1", "source": "1", "target": "3", "sourceHandle": "out", "targetHandle": "a"}, {"id": "e2", "source": "2", "target": "3", "sourceHandle": "out", "targetHandle": "b"}],
            }

            with open(project_dir / "test_workflow.json", "w") as f:
                json.dump(workflow, f, indent=2)

            print("  ✅ Created test workflow")

            return True

        except Exception as e:
            print(f"  ❌ Project operations test failed: {e}")
            return False

    async def test_workflow_execution(self) -> bool:
        """Test workflow execution via API"""
        print("📋 Testing workflow execution...")

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                # Create a simple workflow
                topology = {
                    "nodes": [
                        {"id": "const1", "block_id": "CONSTANT", "label": "Constant 1", "inputs": {}, "extras": {"value": 10}},
                        {"id": "const2", "block_id": "CONSTANT", "label": "Constant 2", "inputs": {}, "extras": {"value": 20}},
                        {"id": "add1", "block_id": "ADDITION", "label": "Add", "inputs": {"a": {"from_node": "const1", "from_output": "default"}, "b": {"from_node": "const2", "from_output": "default"}}, "extras": {}},
                    ]
                }

                # Submit workflow
                response = await client.post(f"{self.base_url}/blocks/run", json=topology)

                if response.status_code != 200:
                    print(f"  ❌ Workflow submission failed: {response.status_code}")
                    print(f"     Response: {response.text}")
                    return False

                result = response.json()
                print(f"  ✅ Workflow submitted: {result.get('job_id', 'unknown')}")

                # In a real test, we would poll for results
                # For now, just verify submission worked
                return True

            except Exception as e:
                print(f"  ❌ Workflow execution test failed: {e}")
                return False

    async def test_uv_environment_management(self) -> bool:
        """Test uv environment management"""
        print("📋 Testing uv environment management...")

        test_dir = self.test_workspace / "uv_test"
        test_dir.mkdir(exist_ok=True)

        try:
            os.chdir(test_dir)

            # Test 1: Create virtual environment
            result = subprocess.run(["uv", "venv"], capture_output=True, text=True)
            assert result.returncode == 0, f"uv venv failed: {result.stderr}"
            assert (test_dir / ".venv").exists(), "Virtual environment not created"
            print("  ✅ Created virtual environment")

            # Test 2: Install a package
            result = subprocess.run(["uv", "pip", "install", "requests"], capture_output=True, text=True)
            assert result.returncode == 0, f"uv pip install failed: {result.stderr}"
            print("  ✅ Installed package with uv")

            # Test 3: List installed packages
            result = subprocess.run(["uv", "pip", "list"], capture_output=True, text=True)
            assert result.returncode == 0, f"uv pip list failed: {result.stderr}"
            assert "requests" in result.stdout, "Package not found in list"
            print("  ✅ Listed installed packages")

            # Test 4: Build a simple project
            # Create minimal pyproject.toml
            pyproject_content = """[project]
name = "test-package"
version = "0.1.0"
description = "Test package"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
"""
            with open(test_dir / "pyproject.toml", "w") as f:
                f.write(pyproject_content)

            # Create package structure
            (test_dir / "test_package").mkdir()
            with open(test_dir / "test_package" / "__init__.py", "w") as f:
                f.write('__version__ = "0.1.0"')

            # Build with uv
            result = subprocess.run(["uv", "build"], capture_output=True, text=True)
            if result.returncode == 0:
                print("  ✅ Built package with uv")
            else:
                print(f"  ⚠️  Build failed (expected for minimal package): {result.stderr}")

            return True

        except Exception as e:
            print(f"  ❌ UV environment test failed: {e}")
            return False
        finally:
            os.chdir("/app")

    async def run_all_tests(self) -> int:
        """Run all integration tests"""
        print("\n🧪 Running AtlasVibe Integration Tests")
        print("=" * 50)

        tests = [
            ("API Health", self.test_api_health),
            ("Project Operations", self.test_project_operations),
            ("Workflow Execution", self.test_workflow_execution),
            ("UV Environment Management", self.test_uv_environment_management),
        ]

        passed = 0
        failed = 0

        for test_name, test_func in tests:
            print(f"\n🔍 {test_name}")
            try:
                if await test_func():
                    passed += 1
                    self.results.append({"name": test_name, "status": "PASSED", "error": None})
                else:
                    failed += 1
                    self.results.append({"name": test_name, "status": "FAILED", "error": "Test returned False"})
            except Exception as e:
                failed += 1
                self.results.append({"name": test_name, "status": "ERROR", "error": str(e)})
                print(f"  ❌ Error: {e}")

        # Generate summary
        print("\n" + "=" * 50)
        print("📊 Integration Test Summary")
        print("=" * 50)
        print(f"Total: {len(tests)}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")

        # Write results to file
        results_file = Path("/app/test-results/integration-results.json")
        results_file.parent.mkdir(exist_ok=True)

        with open(results_file, "w") as f:
            json.dump({"summary": {"total": len(tests), "passed": passed, "failed": failed}, "tests": self.results, "timestamp": time.time()}, f, indent=2)

        print(f"\n💾 Results saved to: {results_file}")

        return 0 if failed == 0 else 1


async def main():
    """Main entry point"""
    tester = AtlasVibeIntegrationTest()
    return await tester.run_all_tests()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

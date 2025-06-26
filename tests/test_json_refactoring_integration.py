#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Created integration tests to verify JSON refactoring
# - Test actual file operations with shared utilities
# - Verify atomic writes and error handling
#

"""Integration tests for JSON operations refactoring."""

import tempfile
import json
import time
import threading
from pathlib import Path
from unittest.mock import patch

from captain.utils.block_metadata_generator import (
    generate_app_json,
    generate_block_data_json,
)
from captain.utils.project_structure import (
    update_block_metadata,
)
from captain.utils.venv_manager import VenvManager, CheckResult, CheckStatus


class TestJSONRefactoringIntegration:
    """Integration tests for refactored JSON operations."""

    def test_generate_app_json_creates_file_atomically(self):
        """Test that app.json is created atomically."""
        with tempfile.TemporaryDirectory() as tmpdir:
            block_dir = Path(tmpdir) / "TEST_BLOCK"
            block_dir.mkdir()

            # Generate app.json
            result = generate_app_json(str(block_dir), "TEST_BLOCK")
            assert result is True

            # Verify file exists and is valid JSON
            app_file = block_dir / "app.json"
            assert app_file.exists()

            with open(app_file) as f:
                data = json.load(f)

            assert "rfInstance" in data
            assert data["rfInstance"]["nodes"][0]["data"]["func"] == "TEST_BLOCK"

    def test_update_block_metadata_preserves_data(self):
        """Test that update_block_metadata preserves existing data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            block_dir = Path(tmpdir) / "TEST_BLOCK"
            block_dir.mkdir()

            # Create initial app.json with extra data
            app_json = block_dir / "app.json"
            initial_data = {
                "rfInstance": {
                    "nodes": [
                        {
                            "data": {
                                "func": "OLD_NAME",
                                "label": "OLD_NAME",
                                "custom": "preserved",
                            }
                        }
                    ],
                    "edges": [],
                },
                "extra": "data",
            }
            app_json.write_text(json.dumps(initial_data, indent=2))

            # Update metadata
            update_block_metadata(block_dir, "OLD_NAME", "NEW_NAME")

            # Verify updates and preservation
            with open(app_json) as f:
                updated_data = json.load(f)

            assert updated_data["rfInstance"]["nodes"][0]["data"]["func"] == "NEW_NAME"
            assert updated_data["rfInstance"]["nodes"][0]["data"]["label"] == "NEW_NAME"
            assert updated_data["rfInstance"]["nodes"][0]["data"]["custom"] == "preserved"
            assert updated_data["extra"] == "data"

    def test_venv_manager_log_persistence(self):
        """Test that venv manager logs are saved and loaded correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            block_dir = Path(tmpdir) / "TEST_BLOCK"
            block_dir.mkdir()

            # Create Python file
            py_file = block_dir / "TEST_BLOCK.py"
            py_file.write_text('''
from pkgs.atlasvibe.atlasvibe import atlasvibe

@atlasvibe
def TEST_BLOCK():
    """Test block."""
    return "test"
''')

            manager = VenvManager(block_dir)

            # Create a test log
            test_result = CheckResult(
                name="test",
                status=CheckStatus.SUCCESS,
                message="Test message",
                duration=1.5,
            )

            log_data = {
                "block_name": "TEST_BLOCK",
                "success": True,
                "checks": [test_result.to_dict()],
            }

            # Save log
            log_path = manager._save_log(log_data)
            assert log_path.exists()

            # Load logs
            logs = manager.get_logs(limit=1)
            assert len(logs) == 1
            assert logs[0]["block_name"] == "TEST_BLOCK"
            assert logs[0]["success"] is True
            assert len(logs[0]["checks"]) == 1

    def test_concurrent_json_writes(self):
        """Test that concurrent writes don't corrupt files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "concurrent.json"

            def write_data(thread_id):
                from captain.utils.shared.json_utils import save_json_file

                data = {"thread": thread_id, "data": list(range(100))}
                save_json_file(test_file, data, atomic=True)
                time.sleep(0.01)  # Small delay to increase collision chance

            # Start multiple threads writing to same file
            threads = []
            for i in range(10):
                t = threading.Thread(target=write_data, args=(i,))
                threads.append(t)
                t.start()

            # Wait for all threads
            for t in threads:
                t.join()

            # Verify file is valid JSON
            with open(test_file) as f:
                data = json.load(f)

            # Should have data from one of the threads (last writer wins)
            assert "thread" in data
            assert isinstance(data["thread"], int)
            assert len(data["data"]) == 100

    def test_error_recovery_in_block_metadata(self):
        """Test error recovery when JSON operations fail."""
        with tempfile.TemporaryDirectory() as tmpdir:
            block_dir = Path(tmpdir) / "TEST_BLOCK"
            block_dir.mkdir()

            # Make directory read-only to cause write failure
            block_dir.chmod(0o555)

            try:
                # This should handle the error gracefully
                result = generate_app_json(str(block_dir), "TEST_BLOCK")
                assert result is False  # Should return False on failure
            finally:
                # Restore permissions
                block_dir.chmod(0o755)

    def test_generate_block_data_json_merges_correctly(self):
        """Test that generate_block_data_json merges with existing data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            block_dir = Path(tmpdir) / "TEST_BLOCK"
            block_dir.mkdir()

            # Create Python file with docstring
            py_file = block_dir / "TEST_BLOCK.py"
            py_file.write_text('''
from pkgs.atlasvibe.atlasvibe import atlasvibe

@atlasvibe
def TEST_BLOCK(x: int = 10):
    """Test block for integration.

    This is a longer description.

    Parameters
    ----------
    x : int
        Input value

    Returns
    -------
    int
        Output value
    """
    return x * 2
''')

            # Create existing block_data.json with custom fields
            block_data_file = block_dir / "block_data.json"
            existing_data = {"custom_field": "preserved", "version": "1.0"}
            block_data_file.write_text(json.dumps(existing_data))

            # Generate block data
            result = generate_block_data_json(str(block_dir), "TEST_BLOCK")
            assert result is True

            # Load and verify
            with open(block_data_file) as f:
                data = json.load(f)

            # Check docstring was added
            assert "docstring" in data
            assert data["docstring"]["short_description"] == "Test block for integration."
            assert len(data["docstring"]["parameters"]) == 1
            assert data["docstring"]["parameters"][0]["name"] == "x"

            # Check existing fields preserved
            assert data["custom_field"] == "preserved"
            assert data["version"] == "1.0"

    @patch("captain.utils.shared.json_utils.logger")
    def test_json_error_logging(self, mock_logger):
        """Test that JSON errors are properly logged."""
        from captain.utils.shared.json_utils import load_json_file

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create invalid JSON file
            bad_json = Path(tmpdir) / "bad.json"
            bad_json.write_text("{ invalid json")

            # Try to load it
            result = load_json_file(bad_json)

            # Should return empty dict and log error
            assert result == {}
            mock_logger.error.assert_called()

            # Check error message contains file path
            error_call = mock_logger.error.call_args[0][0]
            assert "bad.json" in error_call
            assert "Invalid JSON" in error_call

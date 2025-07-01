#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Tests for block metadata generator text file operations."""

from unittest.mock import patch

from captain.utils.block_metadata_generator import (
    generate_example_md,
    generate_test_file,
)


class TestBlockMetadataTextOperations:
    """Test that block metadata generator uses text utilities."""

    def test_generate_example_md_uses_text_utils(self, tmp_path):
        """Test that generate_example_md uses save_text_file."""
        block_dir = tmp_path / "TEST_BLOCK"
        block_dir.mkdir()

        # Create a Python file with docstring
        py_file = block_dir / "TEST_BLOCK.py"
        py_file.write_text(
            '''#!/usr/bin/env python3
"""
Test block for demonstration.

This is a longer description.
"""

def TEST_BLOCK():
    pass
'''
        )

        # Mock save_text_file to verify it's called
        with patch("captain.utils.block_metadata_generator.save_text_file") as mock_save:
            mock_save.return_value = True

            result = generate_example_md(str(block_dir), "TEST_BLOCK")

            # Verify save_text_file was called
            assert mock_save.called
            assert result is True

            # Check the arguments
            call_args = mock_save.call_args
            file_path = call_args[0][0]
            content = call_args[0][1]

            assert str(file_path).endswith("example.md")
            assert "TEST_BLOCK" in content
            # The docstring extraction might not work in test environment,
            # but we can verify the text utility was called correctly

    def test_generate_test_file_uses_text_utils(self, tmp_path):
        """Test that generate_test_file uses save_text_file."""
        block_dir = tmp_path / "TEST_BLOCK"
        block_dir.mkdir()

        # Create a Python file
        py_file = block_dir / "TEST_BLOCK.py"
        py_file.write_text(
            '''#!/usr/bin/env python3
"""Test block."""

def TEST_BLOCK(param1: int, param2: str):
    pass
'''
        )

        # Mock save_text_file to verify it's called
        with patch("captain.utils.block_metadata_generator.save_text_file") as mock_save:
            mock_save.return_value = True

            result = generate_test_file(str(block_dir), "TEST_BLOCK")

            # Verify save_text_file was called
            assert mock_save.called
            assert result is True

            # Check the arguments
            call_args = mock_save.call_args
            file_path = call_args[0][0]
            content = call_args[0][1]

            assert str(file_path).endswith("TEST_BLOCK_test_.py")
            assert "class TestTEST_BLOCK:" in content
            assert "def test_test_block_basic" in content

    def test_example_md_not_overwritten(self, tmp_path):
        """Test that existing example.md is not overwritten."""
        block_dir = tmp_path / "TEST_BLOCK"
        block_dir.mkdir()

        # Create existing example.md
        example_file = block_dir / "example.md"
        example_file.write_text("Existing content")

        # Should return True without overwriting
        result = generate_example_md(str(block_dir), "TEST_BLOCK")
        assert result is True
        assert example_file.read_text() == "Existing content"

    def test_test_file_not_overwritten(self, tmp_path):
        """Test that existing test file is not overwritten."""
        block_dir = tmp_path / "TEST_BLOCK"
        block_dir.mkdir()

        # Create existing test file
        test_file = block_dir / "TEST_BLOCK_test_.py"
        test_file.write_text("# Existing tests")

        # Should return True without overwriting
        result = generate_test_file(str(block_dir), "TEST_BLOCK")
        assert result is True
        assert test_file.read_text() == "# Existing tests"

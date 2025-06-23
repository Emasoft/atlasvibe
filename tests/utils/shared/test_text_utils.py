#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Tests for text file utilities."""

from captain.utils.shared.text_utils import (
    load_text_file,
    save_text_file,
    append_text_file,
    update_text_file,
    merge_text_files,
)


class TestTextUtils:
    """Test suite for text file utilities."""

    def test_save_and_load_text_file(self, tmp_path):
        """Test saving and loading a text file."""
        file_path = tmp_path / "test.txt"
        content = "Hello, world!\nThis is a test file.\n"

        # Save the file
        assert save_text_file(file_path, content) is True

        # Load the file
        loaded_content = load_text_file(file_path)
        assert loaded_content == content

    def test_load_nonexistent_file(self, tmp_path):
        """Test loading a nonexistent file returns default."""
        file_path = tmp_path / "nonexistent.txt"

        # Without default
        assert load_text_file(file_path) == ""

        # With custom default
        assert load_text_file(file_path, default="default text") == "default text"

    def test_save_with_parent_creation(self, tmp_path):
        """Test saving creates parent directories if needed."""
        file_path = tmp_path / "nested" / "dir" / "test.txt"
        content = "Test content"

        # Parent directory doesn't exist
        assert not file_path.parent.exists()

        # Save should create parents
        assert save_text_file(file_path, content, create_parents=True) is True
        assert file_path.exists()
        assert load_text_file(file_path) == content

    def test_save_without_parent_creation(self, tmp_path):
        """Test saving fails when parent doesn't exist and create_parents=False."""
        file_path = tmp_path / "nested" / "dir" / "test.txt"
        content = "Test content"

        # Should fail without parent creation
        assert save_text_file(file_path, content, create_parents=False) is False

    def test_atomic_write(self, tmp_path):
        """Test atomic write prevents partial writes."""
        file_path = tmp_path / "atomic_test.txt"
        content = "Original content"

        # Save initial content
        save_text_file(file_path, content)

        # Test that atomic write doesn't leave partial files
        # This is hard to test directly, but we can verify the mechanism works
        new_content = "New content that is much longer than the original"
        assert save_text_file(file_path, new_content, atomic=True) is True
        assert load_text_file(file_path) == new_content

    def test_encoding_support(self, tmp_path):
        """Test different encodings."""
        file_path = tmp_path / "encoded.txt"

        # Test UTF-8 with special characters
        content_utf8 = "UTF-8: Hello 世界 🌍"
        assert save_text_file(file_path, content_utf8, encoding="utf-8") is True
        assert load_text_file(file_path, encoding="utf-8") == content_utf8

        # Test Latin-1
        content_latin1 = "Latin-1: café"
        assert save_text_file(file_path, content_latin1, encoding="latin-1") is True
        assert load_text_file(file_path, encoding="latin-1") == content_latin1

    def test_append_text_file(self, tmp_path):
        """Test appending text to a file."""
        file_path = tmp_path / "append_test.txt"

        # Initial content
        save_text_file(file_path, "Line 1\n")

        # Append more content
        assert append_text_file(file_path, "Line 2\n") is True
        assert load_text_file(file_path) == "Line 1\nLine 2\n"

        # Append to non-existent file with create=True
        new_file = tmp_path / "new_append.txt"
        assert append_text_file(new_file, "First line\n", create_if_missing=True) is True
        assert load_text_file(new_file) == "First line\n"

    def test_append_without_creation(self, tmp_path):
        """Test append fails when file doesn't exist and create_if_missing=False."""
        file_path = tmp_path / "nonexistent.txt"
        assert append_text_file(file_path, "content", create_if_missing=False) is False

    def test_update_text_file(self, tmp_path):
        """Test updating text file with search and replace."""
        file_path = tmp_path / "update_test.txt"
        original = "Hello world!\nThis is a test.\nHello again!"
        save_text_file(file_path, original)

        # Replace all occurrences
        assert update_text_file(file_path, "Hello", "Hi", replace_all=True) is True
        assert load_text_file(file_path) == "Hi world!\nThis is a test.\nHi again!"

        # Replace first occurrence only
        save_text_file(file_path, original)
        assert update_text_file(file_path, "Hello", "Hi", replace_all=False) is True
        assert load_text_file(file_path) == "Hi world!\nThis is a test.\nHello again!"

    def test_update_nonexistent_file(self, tmp_path):
        """Test update on nonexistent file."""
        file_path = tmp_path / "nonexistent.txt"
        assert update_text_file(file_path, "old", "new") is False

    def test_merge_text_files(self, tmp_path):
        """Test merging multiple text files."""
        # Create source files
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file3 = tmp_path / "file3.txt"
        target = tmp_path / "merged.txt"

        save_text_file(file1, "Content from file 1\n")
        save_text_file(file2, "Content from file 2\n")
        save_text_file(file3, "Content from file 3\n")

        # Merge files
        assert merge_text_files([file1, file2, file3], target) is True

        # Check merged content
        expected = "Content from file 1\nContent from file 2\nContent from file 3\n"
        assert load_text_file(target) == expected

    def test_merge_with_separator(self, tmp_path):
        """Test merging files with custom separator."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        target = tmp_path / "merged.txt"

        save_text_file(file1, "Part 1")
        save_text_file(file2, "Part 2")

        # Merge with separator
        assert merge_text_files([file1, file2], target, separator="\n---\n") is True
        assert load_text_file(target) == "Part 1\n---\nPart 2"

    def test_merge_with_missing_files(self, tmp_path):
        """Test merging handles missing files gracefully."""
        file1 = tmp_path / "exists.txt"
        file2 = tmp_path / "missing.txt"
        target = tmp_path / "merged.txt"

        save_text_file(file1, "Only this exists\n")

        # Should still work with missing files
        assert merge_text_files([file1, file2], target) is True
        assert load_text_file(target) == "Only this exists\n"

    def test_line_ending_preservation(self, tmp_path):
        """Test that line endings are handled correctly."""
        file_path = tmp_path / "line_endings.txt"

        # Test with LF line endings
        content_lf = "Line 1\nLine 2\nLine 3"
        save_text_file(file_path, content_lf)
        assert load_text_file(file_path) == content_lf

        # Test with mixed content including newlines
        mixed_content = "Line 1\nLine 2\n\nLine 4 with spaces    \nLine 5"
        save_text_file(file_path, mixed_content)
        assert load_text_file(file_path) == mixed_content

    def test_large_file_handling(self, tmp_path):
        """Test handling of large text files."""
        file_path = tmp_path / "large.txt"

        # Create a large text content (10MB)
        large_content = "x" * (10 * 1024 * 1024)

        # Should handle large files efficiently
        assert save_text_file(file_path, large_content) is True
        assert len(load_text_file(file_path)) == len(large_content)

    def test_concurrent_access_safety(self, tmp_path):
        """Test that atomic writes prevent corruption during concurrent access."""
        file_path = tmp_path / "concurrent.txt"

        # This is a basic test - in practice, atomic writes help prevent
        # corruption when multiple processes write to the same file
        content1 = "Content from process 1" * 100
        content2 = "Content from process 2" * 100

        # Both writes should succeed without corruption
        assert save_text_file(file_path, content1, atomic=True) is True
        assert save_text_file(file_path, content2, atomic=True) is True

        # Final content should be complete (not corrupted)
        final_content = load_text_file(file_path)
        assert final_content == content2
        assert "Content from process 1" not in final_content

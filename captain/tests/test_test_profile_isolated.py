#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Created isolated unit tests for test_profile error handling
# - Tests GitError and ProfileError exception handling
# - Tests don't require full app import
#

"""
Isolated unit tests for test_profile error handling functionality.
"""

import pytest
from unittest.mock import Mock, patch

# Test the custom exceptions directly
from captain.routes.test_profile import GitError, ProfileError

# Import the functions we need to test
from captain.routes.test_profile import (
    get_profile_path_from_url,
    verify_git_install,
    get_commit_hash,
    update_to_origin_main,
)


class TestCustomExceptions:
    """Test custom exception classes."""

    def test_git_error_creation(self):
        """Test GitError exception creation."""
        error = GitError("Test git error")
        assert str(error) == "Test git error"
        assert isinstance(error, Exception)

    def test_profile_error_creation(self):
        """Test ProfileError exception creation."""
        error = ProfileError("Test profile error")
        assert str(error) == "Test profile error"
        assert isinstance(error, Exception)


class TestHelperFunctions:
    """Test helper functions with error handling."""

    def test_get_profile_path_from_url(self):
        """Test extracting profile name from URL."""
        # Test with .git extension
        url = "https://github.com/user/test-repo.git"
        profiles_path = "/path/to/profiles"
        result = get_profile_path_from_url(profiles_path, url)
        assert result == "/path/to/profiles/test-repo"

        # Test without .git extension
        url = "https://github.com/user/another-repo"
        result = get_profile_path_from_url(profiles_path, url)
        assert result == "/path/to/profiles/another-repo"

    @patch("captain.routes.test_profile.subprocess.run")
    def test_verify_git_install_success(self, mock_run):
        """Test successful git verification."""
        mock_run.return_value = Mock(returncode=0)

        # Should not raise exception
        verify_git_install()

        # Verify subprocess was called correctly
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert call_args == ["git", "--version"]

    @patch("captain.routes.test_profile.subprocess.run")
    def test_verify_git_install_failure(self, mock_run):
        """Test git verification failure."""
        mock_run.return_value = Mock(returncode=1)

        # Should raise RuntimeError
        with pytest.raises(RuntimeError) as exc_info:
            verify_git_install()

        assert "Git is not found on your system" in str(exc_info.value)

    @patch("captain.routes.test_profile.subprocess.run")
    def test_get_commit_hash_success(self, mock_run):
        """Test successful commit hash retrieval."""
        mock_run.return_value = Mock(returncode=0, stdout=b"abc123def456\n")

        result = get_commit_hash("/path/to/repo")
        assert result == "abc123def456"

        # Verify subprocess was called correctly
        call_args = mock_run.call_args[0][0]
        assert call_args == ["git", "-C", "/path/to/repo", "rev-parse", "HEAD"]

    @patch("captain.routes.test_profile.subprocess.run")
    def test_get_commit_hash_failure(self, mock_run):
        """Test commit hash retrieval failure."""
        mock_run.return_value = Mock(returncode=128)

        with pytest.raises(GitError) as exc_info:
            get_commit_hash("/path/to/repo")

        assert "Failed to get commit hash" in str(exc_info.value)
        assert "(code: 128)" in str(exc_info.value)

    @patch("captain.routes.test_profile.subprocess.run")
    def test_update_to_origin_main_clean_repo(self, mock_run):
        """Test updating clean repo to origin/main."""

        # Setup mock responses for different git commands
        def mock_subprocess_run(cmd, **kwargs):
            if "status" in cmd and "--porcelain" in cmd:
                # Clean repo
                return Mock(returncode=0, stdout=b"", stderr=b"")
            elif "fetch" in cmd:
                return Mock(returncode=0, stdout=b"", stderr=b"")
            elif "checkout" in cmd and "origin/main" in cmd:
                return Mock(returncode=0, stdout=b"", stderr=b"")
            return Mock(returncode=0)

        mock_run.side_effect = mock_subprocess_run

        # Should complete without errors
        update_to_origin_main("/path/to/repo")

        # Verify all git commands were called
        assert mock_run.call_count == 3

    @patch("captain.routes.test_profile.subprocess.run")
    def test_update_to_origin_main_dirty_repo(self, mock_run):
        """Test updating dirty repo raises ProfileError."""
        # Mock dirty repo status
        mock_run.return_value = Mock(
            returncode=0, stdout=b"M modified_file.py\n", stderr=b""
        )

        with pytest.raises(ProfileError) as exc_info:
            update_to_origin_main("/path/to/repo")

        assert "Repository has uncommitted changes" in str(exc_info.value)

    @patch("captain.routes.test_profile.subprocess.run")
    def test_update_to_origin_main_fetch_failure(self, mock_run):
        """Test fetch failure with connection error."""

        def mock_subprocess_run(cmd, **kwargs):
            if "status" in cmd:
                return Mock(returncode=0, stdout=b"", stderr=b"")
            elif "fetch" in cmd:
                return Mock(
                    returncode=1,
                    stdout=b"",
                    stderr=b"fatal: unable to access 'https://github.com/...': Could not resolve host",
                )
            return Mock(returncode=0)

        mock_run.side_effect = mock_subprocess_run

        with pytest.raises(ConnectionError) as exc_info:
            update_to_origin_main("/path/to/repo")

        assert "Unable to connect to repository" in str(exc_info.value)


class TestErrorCodeMapping:
    """Test error code generation from exceptions."""

    def test_git_error_code_mapping(self):
        """Test that GitError maps to correct error code."""
        from captain.utils.fastapi_error_handler import _get_error_code

        error = GitError("Test error")
        code = _get_error_code(error)
        assert code == "GIT_OPERATION_FAILED"

    def test_profile_error_code_mapping(self):
        """Test that ProfileError maps to correct error code."""
        from captain.utils.fastapi_error_handler import _get_error_code

        error = ProfileError("Test error")
        code = _get_error_code(error)
        assert code == "PROFILE_ERROR"


class TestErrorSanitization:
    """Test error message sanitization."""

    def test_git_error_sanitization(self):
        """Test that GitError messages are preserved."""
        from captain.utils.fastapi_error_handler import sanitize_error_details

        error = GitError("Repository not found or access denied")
        result = sanitize_error_details(error)
        # GitError messages should be preserved as they're user-facing
        assert result == "Repository not found or access denied"

    def test_profile_error_sanitization(self):
        """Test that ProfileError messages are preserved."""
        from captain.utils.fastapi_error_handler import sanitize_error_details

        error = ProfileError("Repository has uncommitted changes")
        result = sanitize_error_details(error)
        # ProfileError messages should be preserved as they're user-facing
        assert result == "Repository has uncommitted changes"

    def test_generic_error_sanitization(self):
        """Test that generic errors are sanitized."""
        from captain.utils.fastapi_error_handler import sanitize_error_details

        error = RuntimeError("Database password: secret123")
        result = sanitize_error_details(error)
        # Should return generic message
        assert result == "An internal error occurred. Please check logs for details."
        assert "secret123" not in result


# Run tests with: uv run pytest captain/tests/test_test_profile_isolated.py -v

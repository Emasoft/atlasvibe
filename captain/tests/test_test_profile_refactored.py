#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Created comprehensive tests for refactored test_profile.py
# - Tests standardized error handling and JSON utilities
# - Following TDD methodology
#

"""
Test suite for refactored test_profile.py with standardized error handling.
"""

import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient

# Import the app for testing
from captain.main import app


class TestTestProfileRefactored:
    """Test refactored test_profile endpoints with standardized error handling."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_subprocess(self):
        """Mock subprocess.run for git commands."""
        with patch("captain.routes.test_profile.subprocess.run") as mock:
            # Default to successful git commands
            mock.return_value = Mock(returncode=0, stdout=b"mock output", stderr=b"")
            yield mock

    @pytest.fixture
    def mock_os_path(self):
        """Mock os.path functions."""
        with patch("captain.routes.test_profile.os.path") as mock_path:
            mock_path.exists.return_value = False  # Default to not exists
            mock_path.join = lambda *args: "/".join(args)
            yield mock_path

    @pytest.fixture
    def mock_makedirs(self):
        """Mock os.makedirs."""
        with patch("captain.routes.test_profile.os.makedirs") as mock:
            yield mock

    def test_install_success_new_repo(
        self, client, mock_subprocess, mock_os_path, mock_makedirs
    ):
        """Test successful installation of new repository."""
        # Setup
        test_url = "https://github.com/user/test-repo.git"
        mock_subprocess.return_value.stdout = b"abc123def456"  # Commit hash

        # Execute
        response = client.get("/test_profile/install/", headers={"url": test_url})

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "profile_root" in data
        assert data["profile_root"].endswith("test_profiles/test-repo")
        assert data["hash"] == "abc123def456"

        # Verify git clone was called
        clone_call = None
        for call_args in mock_subprocess.call_args_list:
            if "clone" in call_args[0][0]:
                clone_call = call_args
                break
        assert clone_call is not None
        assert "--depth" in clone_call[0][0]
        assert test_url in clone_call[0][0]

    def test_install_success_existing_repo(
        self, client, mock_subprocess, mock_os_path, mock_makedirs
    ):
        """Test successful installation when repository already exists."""
        # Setup
        test_url = "https://github.com/user/test-repo.git"
        mock_os_path.exists.return_value = True  # Repo exists
        mock_subprocess.return_value.stdout = b"abc123def456"

        # Execute
        response = client.get("/test_profile/install/", headers={"url": test_url})

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["hash"] == "abc123def456"

        # Verify update_to_origin_main logic was called
        fetch_call = None
        checkout_call = None
        for call_args in mock_subprocess.call_args_list:
            if "fetch" in call_args[0][0]:
                fetch_call = call_args
            elif "checkout" in call_args[0][0] and "origin/main" in call_args[0][0]:
                checkout_call = call_args

        assert fetch_call is not None
        assert checkout_call is not None

    def test_install_git_not_installed(self, client, mock_subprocess):
        """Test error when git is not installed."""
        # Setup
        test_url = "https://github.com/user/test-repo.git"
        mock_subprocess.return_value.returncode = 1  # Git not found

        # Execute
        response = client.get("/test_profile/install/", headers={"url": test_url})

        # Assert
        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert "code" in data["error"]
        assert data["error"]["code"] == "TEST_PROFILE_SYSTEM_ERROR"
        assert "Git is not found" not in data["error"]["message"]  # Should be sanitized

    def test_install_clone_failure(
        self, client, mock_subprocess, mock_os_path, mock_makedirs
    ):
        """Test error when git clone fails."""
        # Setup
        test_url = "https://github.com/user/test-repo.git"

        def mock_run(cmd, **kwargs):
            if "clone" in cmd:
                return Mock(
                    returncode=1,
                    stdout=b"",
                    stderr=b"fatal: repository not found",
                )
            return Mock(returncode=0, stdout=b"output", stderr=b"")

        mock_subprocess.side_effect = mock_run

        # Execute
        response = client.get("/test_profile/install/", headers={"url": test_url})

        # Assert
        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "TEST_PROFILE_CLONE_FAILED"
        assert "repository not found" not in data["error"]["message"]  # Sanitized

    def test_install_dirty_repo_update(
        self, client, mock_subprocess, mock_os_path, mock_makedirs
    ):
        """Test error when existing repo has uncommitted changes."""
        # Setup
        test_url = "https://github.com/user/test-repo.git"
        mock_os_path.exists.return_value = True  # Repo exists

        def mock_run(cmd, **kwargs):
            if "status" in cmd and "--porcelain" in cmd:
                return Mock(
                    returncode=0, stdout=b"M modified_file.py", stderr=b""
                )  # Dirty repo
            return Mock(returncode=0, stdout=b"output", stderr=b"")

        mock_subprocess.side_effect = mock_run

        # Execute
        response = client.get("/test_profile/install/", headers={"url": test_url})

        # Assert
        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "TEST_PROFILE_REPO_DIRTY"
        assert "modified_file.py" not in data["error"]["message"]  # Sanitized

    def test_checkout_success(self, client, mock_subprocess, mock_os_path):
        """Test successful checkout to specific commit."""
        # Setup
        test_url = "https://github.com/user/test-repo.git"
        target_hash = "def456ghi789"
        current_hash = "abc123def456"

        def mock_run(cmd, **kwargs):
            if "rev-parse" in cmd:
                return Mock(
                    returncode=0,
                    stdout=current_hash.encode()
                    if current_hash == "abc123def456"
                    else target_hash.encode(),
                    stderr=b"",
                )
            return Mock(returncode=0, stdout=b"output", stderr=b"")

        mock_subprocess.side_effect = mock_run

        # Execute
        response = client.post(
            f"/test_profile/checkout/{target_hash}/", headers={"url": test_url}
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["hash"] == current_hash  # Should return current hash

    def test_checkout_fetch_failure(self, client, mock_subprocess, mock_os_path):
        """Test error when git fetch fails during checkout."""
        # Setup
        test_url = "https://github.com/user/test-repo.git"
        target_hash = "def456ghi789"

        def mock_run(cmd, **kwargs):
            if "rev-parse" in cmd:
                return Mock(returncode=0, stdout=b"abc123def456", stderr=b"")
            elif "fetch" in cmd:
                return Mock(
                    returncode=1,
                    stdout=b"",
                    stderr=b"fatal: unable to access repository",
                )
            return Mock(returncode=0, stdout=b"output", stderr=b"")

        mock_subprocess.side_effect = mock_run

        # Execute
        response = client.post(
            f"/test_profile/checkout/{target_hash}/", headers={"url": test_url}
        )

        # Assert
        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "TEST_PROFILE_FETCH_FAILED"
        assert "unable to access" not in data["error"]["message"]  # Sanitized

    def test_checkout_invalid_commit(self, client, mock_subprocess, mock_os_path):
        """Test error when checking out invalid commit."""
        # Setup
        test_url = "https://github.com/user/test-repo.git"
        target_hash = "invalid_hash"

        def mock_run(cmd, **kwargs):
            if "checkout" in cmd and target_hash in cmd:
                return Mock(
                    returncode=1,
                    stdout=b"",
                    stderr=b"error: pathspec 'invalid_hash' did not match",
                )
            return Mock(returncode=0, stdout=b"abc123def456", stderr=b"")

        mock_subprocess.side_effect = mock_run

        # Execute
        response = client.post(
            f"/test_profile/checkout/{target_hash}/", headers={"url": test_url}
        )

        # Assert
        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "TEST_PROFILE_CHECKOUT_FAILED"
        assert "pathspec" not in data["error"]["message"]  # Sanitized

    def test_standardized_error_response_format(self, client, mock_subprocess):
        """Test that all error responses follow standardized format."""
        # Setup to trigger an error
        test_url = "https://github.com/user/test-repo.git"
        mock_subprocess.return_value.returncode = 1  # Git error

        # Execute
        response = client.get("/test_profile/install/", headers={"url": test_url})

        # Assert error response structure
        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        error = data["error"]

        # Check required fields
        assert "code" in error
        assert "message" in error
        assert "timestamp" in error
        assert "request_id" in error

        # Check format
        assert error["code"].startswith("TEST_PROFILE_")
        assert error["request_id"].startswith("req-")
        assert len(error["request_id"]) == 16  # req- + 12 hex chars

    def test_retry_on_transient_failures(
        self, client, mock_subprocess, mock_os_path, mock_makedirs
    ):
        """Test that transient failures are retried."""
        # Setup
        test_url = "https://github.com/user/test-repo.git"
        call_count = 0

        def mock_run(cmd, **kwargs):
            nonlocal call_count
            if "clone" in cmd:
                call_count += 1
                if call_count < 3:
                    # Fail first 2 times
                    return Mock(
                        returncode=1,
                        stdout=b"",
                        stderr=b"fatal: unable to connect",
                    )
                # Succeed on 3rd try
                return Mock(returncode=0, stdout=b"", stderr=b"")
            elif "rev-parse" in cmd:
                return Mock(returncode=0, stdout=b"abc123def456", stderr=b"")
            return Mock(returncode=0, stdout=b"output", stderr=b"")

        mock_subprocess.side_effect = mock_run

        # Execute
        response = client.get("/test_profile/install/", headers={"url": test_url})

        # Assert
        assert response.status_code == 200
        assert call_count == 3  # Should have retried twice

    @pytest.mark.parametrize(
        "exception_type,expected_code",
        [
            (RuntimeError("Git not found"), "TEST_PROFILE_SYSTEM_ERROR"),
            (Exception("Clone failed"), "TEST_PROFILE_INTERNAL_ERROR"),
            (OSError("File system error"), "TEST_PROFILE_SYSTEM_ERROR"),
            (ConnectionError("Network error"), "TEST_PROFILE_CONNECTION_FAILED"),
        ],
    )
    def test_error_code_mapping(
        self, client, mock_subprocess, exception_type, expected_code
    ):
        """Test that different exceptions map to appropriate error codes."""
        # Setup
        test_url = "https://github.com/user/test-repo.git"

        def mock_run(cmd, **kwargs):
            if "--version" in cmd:
                raise exception_type

        mock_subprocess.side_effect = mock_run

        # Execute
        response = client.get("/test_profile/install/", headers={"url": test_url})

        # Assert
        assert response.status_code == 500
        data = response.json()
        assert data["error"]["code"] == expected_code


# Run tests with: uv run pytest captain/tests/test_test_profile_refactored.py -v

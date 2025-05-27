// conftest.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - `prefect_test_settings` fixture:
#   - Configures Prefect to run with ephemeral API server enabled during tests.
#   - Sets `PREFECT_HOME` to a temporary directory for test isolation.
#   - Disables project usage stats.
#   - Sets `PREFECT_TEST_MODE` to "true" for test environment.
#   - Restores original environment variables after tests.
#
# Copyright (c) 2024 Emasoft
#
# This software is licensed under the MIT License.
# Refer to the LICENSE file for more details.

import pytest
import os
import tempfile

@pytest.fixture(scope="session", autouse=True)
def prefect_test_settings():
    """Configure Prefect for testing with ephemeral API server."""
    original_env = {
        "PREFECT_API_EPHEMERAL_SERVER_ENABLED": os.environ.get("PREFECT_API_EPHEMERAL_SERVER_ENABLED"),
        "PREFECT_HOME": os.environ.get("PREFECT_HOME"),
        "PREFECT_SETTINGS_SEND_PROJECT_USAGE_STATS": os.environ.get("PREFECT_SETTINGS_SEND_PROJECT_USAGE_STATS"),
        "PREFECT_TEST_MODE": os.environ.get("PREFECT_TEST_MODE"),
    }

    # Set test environment variables
    os.environ["PREFECT_API_EPHEMERAL_SERVER_ENABLED"] = "true"
    os.environ["PREFECT_HOME"] = str(tempfile.mkdtemp(prefix="prefect_home"))
    os.environ["PREFECT_SETTINGS_SEND_PROJECT_USAGE_STATS"] = "false"
    os.environ["PREFECT_TEST_MODE"] = "true"

    yield

    # Restore original environment variables
    for key, value in original_env.items():
        if value is None:
            if key in os.environ:
                del os.environ[key]
        else:
            os.environ[key] = value

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Mock tm_devices to prevent hanging during tests."""

import sys
from unittest.mock import MagicMock


class MockDeviceManager:
    """Mock DeviceManager that doesn't hang."""

    def __init__(self, verbose=False):
        self.verbose = verbose
        self.visa_library = None

    def remove_all_devices(self):
        """Mock remove_all_devices."""
        pass


# Create mock module
mock_tm_devices = MagicMock()
mock_tm_devices.DeviceManager = MockDeviceManager
mock_tm_devices.helpers.PYVISA_PY_BACKEND = "pyvisa-py"

# Mock the PIDevice as well
mock_tm_devices.drivers.pi.pi_device.PIDevice = MagicMock


def install_mock():
    """Install the mock into sys.modules."""
    sys.modules["tm_devices"] = mock_tm_devices
    sys.modules["tm_devices.helpers"] = mock_tm_devices.helpers
    sys.modules["tm_devices.drivers"] = mock_tm_devices.drivers
    sys.modules["tm_devices.drivers.pi"] = mock_tm_devices.drivers.pi
    sys.modules["tm_devices.drivers.pi.pi_device"] = (
        mock_tm_devices.drivers.pi.pi_device
    )

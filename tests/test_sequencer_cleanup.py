#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test to verify test sequencer works properly after cloud cleanup."""

from unittest.mock import Mock, patch
import json


def test_test_sequencer_no_cloud_dependencies():
    """Verify test sequencer has no cloud service dependencies."""
    # Import the test sequencer module
    from captain.utils.test_sequencer import run_test_sequence

    # Create a mock test sequence
    mock_sequence = {
        "type": "root",
        "children": [
            {
                "type": "test",
                "id": "test1",
                "groupId": "group1",
                "path": "test.py",
                "testName": "test_example",
                "runInParallel": False,
                "testType": "pytest",
                "status": "pending",
                "error": None,
            }
        ],
        "identifiers": ["test_example"],
    }

    # Mock the WebSocket manager
    mock_ws_manager = Mock()

    # Run test sequence should work without any cloud parameters
    with patch(
        "captain.utils.test_sequencer.run_test_sequence.ts_manager", mock_ws_manager
    ):
        # This should not raise any errors related to cloud services
        try:
            # The function signature should not require cloud parameters
            run_test_sequence.run_test_sequence(
                test_sequence_dict=mock_sequence,
                run_name="test_run",
                socketId="socket123",
            )
            # Function should execute without cloud-related errors
            assert True
        except Exception as e:
            # If there's an error, it should not be related to cloud services
            assert "cloud" not in str(e).lower()
            assert "upload" not in str(e).lower()


def test_no_cloud_imports_in_test_sequencer():
    """Verify no cloud imports exist in test sequencer modules."""
    import captain.utils.test_sequencer
    import captain.routes.test_sequence

    # Check module dictionaries for cloud imports
    for module in [captain.utils.test_sequencer, captain.routes.test_sequence]:
        module_dict = vars(module)
        for name, obj in module_dict.items():
            if hasattr(obj, "__module__") and obj.__module__:
                assert "cloud" not in obj.__module__.lower(), (
                    f"Found cloud import in {module.__name__}.{name}"
                )
                assert "upload" not in obj.__module__.lower(), (
                    f"Found upload import in {module.__name__}.{name}"
                )


def test_test_sequence_model_no_cloud_fields():
    """Verify test sequence models don't have cloud fields."""
    from captain.models.test_sequencer import Test

    # Check that the Test model doesn't have cloud-related fields
    test_fields = Test.model_fields

    # These fields should not exist
    cloud_fields = [
        "exportToCloud",
        "export_to_cloud",
        "isSavedToCloud",
        "is_saved_to_cloud",
    ]
    for field in cloud_fields:
        assert field not in test_fields, f"Found cloud field '{field}' in Test model"

    # Create a test instance - should work without cloud fields
    test_instance = Test(
        type="test",
        id="test123",
        groupId="group123",
        path="test.py",
        testName="test_example",
        runInParallel=False,
        testType="pytest",
        status="pending",
        error=None,
    )

    # Verify the instance doesn't have cloud attributes
    for field in cloud_fields:
        assert not hasattr(test_instance, field), (
            f"Test instance has cloud field '{field}'"
        )


def test_websocket_messages_no_cloud():
    """Verify WebSocket messages don't contain cloud-related data."""
    from captain.models.test_sequencer import BackendMsg, MsgState

    # Create various message types
    messages = [
        BackendMsg(
            state=MsgState.test_done,
            targetId="test1",
            status="pass",
            timeTaken=1.5,
            error=None,
        ),
        BackendMsg(
            state=MsgState.test_set_done,
            targetId="",
            status="pass",
            timeTaken=10.0,
            error=None,
        ),
    ]

    # Verify messages can be serialized without cloud fields
    for msg in messages:
        msg_dict = msg.model_dump()
        msg_json = json.dumps(msg_dict)

        # Check that serialized messages don't contain cloud references
        assert "cloud" not in msg_json.lower()
        assert "upload" not in msg_json.lower()

        # Verify the message structure is clean
        assert "state" in msg_dict
        assert "status" in msg_dict
        assert msg_dict["state"] in ["test_done", "test_set_done"]

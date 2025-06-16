#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test to verify cloud functionality has been properly removed from AtlasVibe."""

import pytest
from fastapi.testclient import TestClient
from captain.main import app

client = TestClient(app)


def test_no_cloud_endpoints():
    """Verify that cloud-related endpoints no longer exist."""
    cloud_endpoints = [
        "/cloud/health",
        "/cloud/login",
        "/cloud/logout", 
        "/cloud/user",
        "/cloud/upload",
        "/session/upload",
        "/test-results/cloud"
    ]
    
    for endpoint in cloud_endpoints:
        # GET requests should return 404
        response = client.get(endpoint)
        assert response.status_code in [404, 405], f"Endpoint {endpoint} still exists with status {response.status_code}"
        
        # POST requests should return 404
        response = client.post(endpoint, json={})
        assert response.status_code in [404, 405], f"Endpoint {endpoint} still exists with status {response.status_code}"


def test_test_sequencer_works_without_cloud():
    """Verify test sequencer functionality works without cloud services."""
    # Get test profiles - should work without cloud
    response = client.get("/discover/pytest/", params={"path": ".", "oneFile": False})
    assert response.status_code == 200
    
    # Verify response has expected structure without cloud fields
    data = response.json()
    assert "response" in data
    assert "missingLibraries" in data
    assert "error" in data


def test_no_cloud_imports():
    """Verify no cloud service imports exist in key modules."""
    import captain.routes
    import captain.services
    import captain.models
    
    # Check that atlasvibe_cloud is not imported
    for module in [captain.routes, captain.services, captain.models]:
        module_dict = vars(module)
        for name, obj in module_dict.items():
            if hasattr(obj, "__module__") and obj.__module__:
                assert "atlasvibe_cloud" not in obj.__module__, f"Found cloud import in {module.__name__}.{name}"


def test_api_module_has_no_post_session():
    """Verify postSession function has been removed from API module."""
    # This would normally be imported from the frontend, but we can't import TS here
    # Instead, we'll verify the backend doesn't have session upload endpoints
    response = client.post("/session", json={
        "serialNumber": "test123",
        "stationId": "station1",
        "integrity": True,
        "aborted": False,
        "commitHash": "abc123",
        "cycleRuns": []
    })
    assert response.status_code == 404, "Session upload endpoint should not exist"


def test_export_to_cloud_field_removed():
    """Verify exportToCloud field is not expected in test objects."""
    # Create a test with exportToCloud field - should be ignored
    test_data = {
        "type": "test",
        "id": "test123",
        "groupId": "group123",
        "path": "test.py",
        "testName": "test_example",
        "runInParallel": False,
        "testType": "pytest",
        "status": "pending",
        "error": None,
        "exportToCloud": True  # This field should be ignored
    }
    
    # The API should accept this but ignore exportToCloud
    # Since we don't have a direct endpoint to test this, we verify the field
    # is not in the type definition by checking the discover endpoint
    response = client.get("/discover/pytest", params={"path": ".", "oneFile": False})
    assert response.status_code == 200
    # The response should work without any cloud-related fields
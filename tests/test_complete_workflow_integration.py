#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Comprehensive integration test for the complete AtlasVibe workflow.

This test verifies the entire system working together:
1. Blueprint → Instance creation
2. Automatic metadata generation
3. Code editing and regeneration
4. Complete independence between blueprints and instances
"""

import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from captain.main import app
from captain.utils.project_structure import (
    copy_blueprint_to_project,
    initialize_project_structure,
    get_project_blocks_dir,
    validate_project_structure
)
from captain.utils.block_metadata_generator import (
    generate_all_metadata_files,
    regenerate_block_data_json
)


class TestCompleteWorkflowIntegration:
    """Test the complete AtlasVibe workflow from end to end."""

    @pytest.fixture
    def test_client(self):
        """Create a test client for the FastAPI app."""
        return TestClient(app)

    @pytest.fixture
    def blueprint_setup(self):
        """Set up a test blueprint in a temporary directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create blueprint structure
            blueprint_base = Path(tmpdir) / "blocks" / "TEST_CATEGORY"
            blueprint_dir = blueprint_base / "SAMPLE_BLUEPRINT"
            blueprint_dir.mkdir(parents=True)
            
            # Create blueprint files
            py_content = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from atlasvibe import atlasvibe
from atlasvibe.parameter_types import String, Number, Vector


@atlasvibe
def SAMPLE_BLUEPRINT(
    text_input: String = "Default text",
    multiplier: Number = 1.0
) -> Vector:
    """
    Sample blueprint for integration testing.
    
    This blueprint demonstrates the complete workflow of AtlasVibe's
    blueprint → instance model with automatic metadata generation.
    
    Parameters
    ----------
    text_input : String
        Text input to process
    multiplier : Number
        Multiplication factor
        
    Returns
    -------
    Vector
        Output vector with processed values
    """
    return [len(text_input) * multiplier for _ in range(3)]
'''
            
            (blueprint_dir / "SAMPLE_BLUEPRINT.py").write_text(py_content)
            
            # Create initial metadata
            app_data = {
                "rfInstance": {
                    "nodes": [{
                        "id": "1",
                        "type": "atlasvibe_block",
                        "position": {"x": 100, "y": 100},
                        "data": {
                            "label": "SAMPLE_BLUEPRINT",
                            "func": "SAMPLE_BLUEPRINT"
                        }
                    }],
                    "edges": []
                }
            }
            (blueprint_dir / "app.json").write_text(json.dumps(app_data, indent=2))
            (blueprint_dir / "example.md").write_text("Sample blueprint example")
            
            yield str(blueprint_dir), str(tmpdir)

    @pytest.fixture
    def project_setup(self):
        """Set up a test project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_file = Path(tmpdir) / "test_project.atlasvibe"
            project_data = {
                "version": "1.0",
                "name": "Test Project",
                "blocks": []
            }
            project_file.write_text(json.dumps(project_data))
            
            # Initialize project structure
            initialize_project_structure(str(project_file))
            
            yield str(project_file)

    def test_complete_workflow_blueprint_to_instance_to_edit(self, blueprint_setup, project_setup, test_client):
        """Test the complete workflow from blueprint to instance to edited instance."""
        blueprint_path, blocks_base = blueprint_setup
        project_path = project_setup
        
        print("\n=== COMPLETE WORKFLOW INTEGRATION TEST ===\n")
        
        # Step 1: Verify project structure
        assert validate_project_structure(project_path)
        project_blocks_dir = get_project_blocks_dir(project_path)
        assert project_blocks_dir.exists()
        print("✓ Step 1: Project structure validated")
        
        # Step 2: Create instance from blueprint (simulating drag & drop)
        instance_name = "SAMPLE_BLUEPRINT_1"
        instance_path = copy_blueprint_to_project(
            blueprint_path,
            project_path,
            instance_name
        )
        
        # Verify instance was created
        instance_dir = Path(instance_path)
        assert instance_dir.exists()
        assert instance_dir.name == instance_name
        print(f"✓ Step 2: Instance created at {instance_path}")
        
        # Step 3: Verify automatic metadata generation
        # Check that block_data.json was regenerated from docstring
        block_data_path = instance_dir / "block_data.json"
        assert block_data_path.exists()
        
        with open(block_data_path) as f:
            block_data = json.load(f)
        
        # Verify docstring was properly extracted
        assert "docstring" in block_data
        assert block_data["docstring"]["short_description"] == "Sample blueprint for integration testing."
        assert len(block_data["docstring"]["parameters"]) == 2
        assert block_data["docstring"]["parameters"][0]["name"] == "text_input"
        assert block_data["docstring"]["parameters"][1]["name"] == "multiplier"
        assert len(block_data["docstring"]["returns"]) == 1
        assert block_data["docstring"]["returns"][0]["type"] == "Vector"
        print("✓ Step 3: Metadata automatically generated from docstring")
        
        # Step 4: Test API endpoint for creating custom block
        with patch('captain.routes.blocks.find_blueprint_path') as mock_find:
            mock_find.return_value = Path(blueprint_path)
            
            response = test_client.post("/blocks/create-custom/", json={
                "blueprint_key": "SAMPLE_BLUEPRINT",
                "new_block_name": "SAMPLE_BLUEPRINT_2",
                "project_path": project_path
            })
            
            assert response.status_code == 200
            result = response.json()
            assert result["key"] == "SAMPLE_BLUEPRINT_2"
            assert "path" in result
            print("✓ Step 4: API endpoint for creating custom blocks works")
        
        # Step 5: Edit instance code (simulating UI editor)
        py_file = instance_dir / f"{instance_name}.py"
        updated_code = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from atlasvibe import atlasvibe
from atlasvibe.parameter_types import String, Number, Matrix


@atlasvibe
def SAMPLE_BLUEPRINT_1(
    modified_text: String = "Modified default",
    scale_factor: Number = 2.5,
    matrix_data: Matrix = [[1, 2], [3, 4]]
) -> Matrix:
    """
    Modified instance demonstrating independence from blueprint.
    
    This instance has been edited through the UI editor, showing
    how instances are completely independent from their blueprints.
    
    Parameters
    ----------
    modified_text : String
        Modified text parameter (renamed)
    scale_factor : Number
        Scale factor (renamed from multiplier)
    matrix_data : Matrix
        New matrix parameter added
        
    Returns
    -------
    Matrix
        Matrix output instead of vector
    """
    rows = len(matrix_data)
    cols = len(matrix_data[0]) if matrix_data else 0
    return [[scale_factor * (i + j) for j in range(cols)] for i in range(rows)]
'''
        
        py_file.write_text(updated_code)
        
        # Step 6: Test metadata regeneration
        success = regenerate_block_data_json(str(instance_dir))
        assert success
        
        # Verify updated metadata
        with open(block_data_path) as f:
            updated_data = json.load(f)
        
        assert updated_data["docstring"]["short_description"] == "Modified instance demonstrating independence from blueprint."
        assert len(updated_data["docstring"]["parameters"]) == 3
        param_names = [p["name"] for p in updated_data["docstring"]["parameters"]]
        assert "modified_text" in param_names
        assert "scale_factor" in param_names
        assert "matrix_data" in param_names
        assert updated_data["docstring"]["returns"][0]["type"] == "Matrix"
        print("✓ Step 6: Metadata regenerated after code edit")
        
        # Step 7: Test API endpoint for updating code
        response = test_client.post("/blocks/update-code/", json={
            "block_path": str(py_file),
            "content": updated_code,
            "project_path": project_path
        })
        
        assert response.status_code == 200
        result = response.json()
        assert "path" in result
        print("✓ Step 7: API endpoint for updating code works")
        
        # Step 8: Verify blueprint remains unchanged
        blueprint_py = Path(blueprint_path) / "SAMPLE_BLUEPRINT.py"
        blueprint_content = blueprint_py.read_text()
        assert "def SAMPLE_BLUEPRINT(" in blueprint_content
        assert "modified_text" not in blueprint_content
        assert "matrix_data" not in blueprint_content
        print("✓ Step 8: Blueprint remains unchanged after instance edit")
        
        # Step 9: Create another instance to verify independence
        instance3_name = "SAMPLE_BLUEPRINT_3"
        instance3_path = copy_blueprint_to_project(
            blueprint_path,
            project_path,
            instance3_name
        )
        
        instance3_dir = Path(instance3_path)
        instance3_py = instance3_dir / f"{instance3_name}.py"
        instance3_content = instance3_py.read_text()
        
        # Verify new instance is based on original blueprint, not modified instance
        assert "text_input" in instance3_content
        assert "multiplier" in instance3_content
        assert "modified_text" not in instance3_content
        assert "matrix_data" not in instance3_content
        print("✓ Step 9: New instances are created from blueprint, not other instances")
        
        # Step 10: List all project blocks
        blocks_list = list(project_blocks_dir.iterdir())
        block_names = [b.name for b in blocks_list if b.is_dir()]
        assert len(block_names) == 3
        assert "SAMPLE_BLUEPRINT_1" in block_names
        assert "SAMPLE_BLUEPRINT_2" in block_names
        assert "SAMPLE_BLUEPRINT_3" in block_names
        print(f"✓ Step 10: Project contains instances: {block_names}")
        
        print("\n🎉 COMPLETE WORKFLOW TEST PASSED!")
        print("\nSummary:")
        print("- Blueprints and instances are completely independent")
        print("- Automatic metadata generation works correctly")
        print("- API endpoints function properly")
        print("- Multiple instances can coexist with different code")
        print("- Blueprint remains unchanged when instances are edited")

    def test_error_handling_invalid_project(self, test_client):
        """Test error handling for invalid project paths."""
        response = test_client.post("/blocks/create-custom/", json={
            "blueprint_key": "SOME_BLOCK",
            "new_block_name": "NEW_BLOCK",
            "project_path": "/invalid/path"
        })
        
        assert response.status_code == 422
        assert "Invalid project path" in response.json()["detail"]

    def test_error_handling_blueprint_not_found(self, test_client, project_setup):
        """Test error handling when blueprint doesn't exist."""
        response = test_client.post("/blocks/create-custom/", json={
            "blueprint_key": "NON_EXISTENT_BLOCK",
            "new_block_name": "NEW_BLOCK",
            "project_path": project_setup
        })
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_error_handling_invalid_block_name(self, test_client, project_setup):
        """Test error handling for invalid block names."""
        # Test with path traversal attempt
        response = test_client.post("/blocks/create-custom/", json={
            "blueprint_key": "SOME_BLOCK",
            "new_block_name": "../../../evil",
            "project_path": project_setup
        })
        
        assert response.status_code == 422
        assert "cannot contain path separators" in response.json()["detail"]
        
        # Test with Python reserved word
        response = test_client.post("/blocks/create-custom/", json={
            "blueprint_key": "SOME_BLOCK",
            "new_block_name": "class",
            "project_path": project_setup
        })
        
        assert response.status_code == 422
        assert "reserved word" in response.json()["detail"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
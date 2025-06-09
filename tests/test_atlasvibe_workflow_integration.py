#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test automatic metadata generation integration with AtlasVibe workflow.

This test verifies that the automatic metadata generation works correctly
with AtlasVibe's clone-and-edit workflow.
"""

import json
import tempfile
import shutil
from pathlib import Path

import pytest

from captain.utils.project_structure import (
    copy_blueprint_to_project,
    initialize_project_structure,
    get_project_blocks_dir
)
from captain.utils.block_metadata_generator import regenerate_block_data_json


class TestAtlasVibeWorkflowIntegration:
    """Test automatic metadata generation with AtlasVibe's actual workflow."""

    @pytest.fixture
    def temp_blueprint(self):
        """Create a temporary blueprint block."""
        with tempfile.TemporaryDirectory() as tmpdir:
            blueprint_dir = Path(tmpdir) / "TEST_BLUEPRINT"
            blueprint_dir.mkdir()
            
            # Create blueprint Python file
            py_content = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from atlasvibe import atlasvibe
from atlasvibe.parameter_types import String, Number


@atlasvibe
def TEST_BLUEPRINT(
    input_text: String = "Original text",
    scale: Number = 1.0
) -> String:
    """
    Test blueprint block for workflow integration.
    
    This block demonstrates the AtlasVibe clone-and-edit workflow
    with automatic metadata generation.
    
    Parameters
    ----------
    input_text : String
        The input text to process
    scale : Number
        Scale factor for processing
        
    Returns
    -------
    String
        Processed text output
    """
    return f"{input_text} (scaled by {scale})"
'''
            
            (blueprint_dir / "TEST_BLUEPRINT.py").write_text(py_content)
            
            # Create initial metadata files
            app_data = {
                "rfInstance": {
                    "nodes": [
                        {
                            "id": "1",
                            "type": "atlasvibe_block",
                            "position": {"x": 100, "y": 100},
                            "data": {
                                "label": "TEST_BLUEPRINT",
                                "func": "TEST_BLUEPRINT"
                            }
                        }
                    ],
                    "edges": []
                }
            }
            (blueprint_dir / "app.json").write_text(json.dumps(app_data, indent=2))
            
            (blueprint_dir / "example.md").write_text("Example for TEST_BLUEPRINT")
            
            block_data = {
                "docstring": {
                    "short_description": "Original blueprint description",
                    "long_description": "",
                    "parameters": [],
                    "returns": []
                }
            }
            (blueprint_dir / "block_data.json").write_text(json.dumps(block_data, indent=2))
            
            yield str(blueprint_dir)

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_file = Path(tmpdir) / "test_project.atlasvibe"
            project_file.write_text("{}")  # Empty project file
            yield str(project_file)

    def test_clone_blueprint_to_custom_block(self, temp_blueprint, temp_project):
        """Test Step 1: Clone/Instance Block workflow."""
        print("\n=== Testing Step 1: Clone Blueprint to Custom Block ===")
        
        # Simulate user dragging a blueprint block to workflow
        new_block_name = "TEST_BLUEPRINT_1"
        
        # This is what happens when user drags a blueprint block
        new_block_path = copy_blueprint_to_project(
            temp_blueprint,
            temp_project,
            new_block_name
        )
        
        print(f"✓ Created custom block at: {new_block_path}")
        
        # Verify the custom block was created correctly
        custom_block_dir = Path(new_block_path)
        assert custom_block_dir.exists()
        assert custom_block_dir.name == new_block_name
        
        # Verify files were copied and renamed
        py_file = custom_block_dir / f"{new_block_name}.py"
        assert py_file.exists()
        
        # Verify function name was updated
        py_content = py_file.read_text()
        assert f"def {new_block_name}(" in py_content
        assert "def TEST_BLUEPRINT(" not in py_content
        print(f"✓ Function name updated to: {new_block_name}")
        
        # Verify app.json was updated
        app_json = custom_block_dir / "app.json"
        assert app_json.exists()
        app_data = json.loads(app_json.read_text())
        node = app_data["rfInstance"]["nodes"][0]
        assert node["data"]["func"] == new_block_name
        assert node["data"]["label"] == new_block_name
        print("✓ app.json updated with new function name")
        
        # Verify block_data.json was regenerated from docstring
        block_data_json = custom_block_dir / "block_data.json"
        assert block_data_json.exists()
        block_data = json.loads(block_data_json.read_text())
        
        # The automatic generation should have updated this from the actual docstring
        assert block_data["docstring"]["short_description"] == "Test blueprint block for workflow integration."
        assert len(block_data["docstring"]["parameters"]) == 2
        assert block_data["docstring"]["parameters"][0]["name"] == "input_text"
        assert block_data["docstring"]["parameters"][1]["name"] == "scale"
        print("✓ block_data.json regenerated from actual docstring")
        
        return new_block_path

    def test_edit_custom_block_code(self, temp_blueprint, temp_project):
        """Test Step 2: Edit Block Code workflow."""
        print("\n=== Testing Step 2: Edit Custom Block Code ===")
        
        # First create a custom block
        new_block_name = "TEST_EDITABLE_BLOCK"
        new_block_path = copy_blueprint_to_project(
            temp_blueprint,
            temp_project,
            new_block_name
        )
        
        custom_block_dir = Path(new_block_path)
        py_file = custom_block_dir / f"{new_block_name}.py"
        
        # Simulate user editing the code in the UI
        updated_code = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from atlasvibe import atlasvibe
from atlasvibe.parameter_types import String, Number, Matrix


@atlasvibe
def TEST_EDITABLE_BLOCK(
    updated_text: String = "Modified text",
    multiplier: Number = 2.5,
    data_matrix: Matrix = [[1, 2], [3, 4]]
) -> Matrix:
    """
    UPDATED: Test block that has been modified by the user.
    
    This block shows how the metadata is automatically regenerated
    when the user edits the code through the integrated UI editor.
    
    Parameters
    ----------
    updated_text : String
        Updated text parameter (renamed from input_text)
    multiplier : Number
        Multiplication factor (renamed from scale)
    data_matrix : Matrix
        New matrix parameter added by user
        
    Returns
    -------
    Matrix
        Matrix result instead of string
    """
    # User's new implementation
    return [[val * multiplier for val in row] for row in data_matrix]
'''
        
        # Write the updated code (simulating the /blocks/update-code/ API)
        py_file.write_text(updated_code)
        
        # Regenerate metadata (this happens automatically in the API)
        success = regenerate_block_data_json(str(custom_block_dir))
        assert success
        print("✓ block_data.json regenerated after code edit")
        
        # Verify the metadata was updated correctly
        block_data_json = custom_block_dir / "block_data.json"
        block_data = json.loads(block_data_json.read_text())
        
        # Check that docstring was updated
        assert block_data["docstring"]["short_description"] == "UPDATED: Test block that has been modified by the user."
        
        # Check that parameters were updated
        params = block_data["docstring"]["parameters"]
        assert len(params) == 3
        param_names = [p["name"] for p in params]
        assert "updated_text" in param_names
        assert "multiplier" in param_names  
        assert "data_matrix" in param_names
        assert "input_text" not in param_names  # Old parameter removed
        
        # Check that return type was updated
        returns = block_data["docstring"]["returns"]
        assert len(returns) == 1
        assert returns[0]["type"] == "Matrix"
        
        print("✓ All metadata correctly updated to reflect code changes")
        print(f"  - Parameters: {param_names}")
        print(f"  - Return type: {returns[0]['type']}")

    def test_duplicate_block_workflow(self, temp_blueprint, temp_project):
        """Test Step 3: Duplicate Existing Block workflow."""
        print("\n=== Testing Step 3: Duplicate Existing Block ===")
        
        # Create first custom block
        original_name = "ORIGINAL_BLOCK"
        original_path = copy_blueprint_to_project(
            temp_blueprint,
            temp_project,
            original_name
        )
        
        # Simulate duplicating the block (creates another custom block)
        duplicate_name = "ORIGINAL_BLOCK_2"
        duplicate_path = copy_blueprint_to_project(
            original_path,  # Source is now the custom block, not blueprint
            temp_project,
            duplicate_name
        )
        
        print(f"✓ Duplicated block: {original_name} → {duplicate_name}")
        
        # Verify both blocks exist and are independent
        original_dir = Path(original_path)
        duplicate_dir = Path(duplicate_path)
        
        assert original_dir.exists()
        assert duplicate_dir.exists()
        assert original_dir != duplicate_dir
        
        # Verify function names are different
        original_py = (original_dir / f"{original_name}.py").read_text()
        duplicate_py = (duplicate_dir / f"{duplicate_name}.py").read_text()
        
        assert f"def {original_name}(" in original_py
        assert f"def {duplicate_name}(" in duplicate_py
        
        print("✓ Both blocks have correct function names")
        print("✓ Duplicate workflow completed successfully")

    def test_complete_atlasvibe_workflow(self, temp_blueprint, temp_project):
        """Test the complete AtlasVibe workflow end-to-end."""
        print("\n=== Testing Complete AtlasVibe Workflow ===")
        
        # Step 1: User drags blueprint to create custom block
        custom_block_path = self.test_clone_blueprint_to_custom_block(temp_blueprint, temp_project)
        
        # Step 2: User edits the custom block code
        self.test_edit_custom_block_code(temp_blueprint, temp_project)
        
        # Step 3: User duplicates an existing block
        self.test_duplicate_block_workflow(temp_blueprint, temp_project)
        
        # Verify project structure
        project_blocks_dir = get_project_blocks_dir(temp_project)
        assert project_blocks_dir.exists()
        
        # Should have multiple custom blocks now
        custom_blocks = [d.name for d in project_blocks_dir.iterdir() if d.is_dir()]
        print(f"\n✓ Project contains custom blocks: {custom_blocks}")
        
        # Each block should have complete metadata
        for block_name in custom_blocks:
            block_dir = project_blocks_dir / block_name
            required_files = [
                f"{block_name}.py",
                "block_data.json",
                "app.json",
                "example.md"
            ]
            
            for file_name in required_files:
                file_path = block_dir / file_name
                assert file_path.exists(), f"Missing {file_name} in {block_name}"
            
            # Verify block_data.json has proper structure
            block_data_path = block_dir / "block_data.json"
            block_data = json.loads(block_data_path.read_text())
            assert "docstring" in block_data
            assert "short_description" in block_data["docstring"]
            assert "parameters" in block_data["docstring"]
            assert "returns" in block_data["docstring"]
            
        print("✓ All custom blocks have complete and valid metadata")
        print("\n🎉 Complete AtlasVibe workflow test PASSED!")


if __name__ == "__main__":
    # Run specific tests
    test_instance = TestAtlasVibeWorkflowIntegration()
    
    # Note: These would need proper fixtures in pytest
    print("AtlasVibe Workflow Integration Test")
    print("=" * 50)
    print("This test verifies that automatic metadata generation")
    print("works correctly with AtlasVibe's clone-and-edit workflow.")
# Copyright (c) 2024 Emasoft (for atlasvibe modifications and derivative work)
# Copyright (c) 2024 Flojoy (for the original "Flojoy Studio" software)
#
# This software is licensed under the MIT License.
# Refer to the LICENSE file for more details.

import pytest
import os
import shutil
import json
from unittest.mock import patch, MagicMock, call

# Hypothetical service modules
# from atlasvibe_engine import block_service, project_service, constants

# For now, let's define placeholder constants
CUSTOM_BLOCKS_DIR_NAME = "atlasvibe_custom_blocks"
PYTHON_FILE_EXT = ".py"
METADATA_APP_JSON = "app.json"
# ... other constants ...
TEST_FILE_SUFFIX = "_test_.py"


# Placeholder for services - In a real app, these would be imported
class MockBlockService:
    def __init__(self, blueprint_base_path="/mock_blueprints"):
        self.blueprint_base_path = blueprint_base_path
        # In a real service, this might query a manifest or scan a directory
        self.available_blueprints = {
            "MATRIX_VIEW": {"path": os.path.join(blueprint_base_path, "MATRIX_VIEW")},
            "ADD": {"path": os.path.join(blueprint_base_path, "ADD")},
            "CONSTANT": {"path": os.path.join(blueprint_base_path, "CONSTANT")},
        }

    def _get_next_available_name_in_project(self, project_custom_blocks_path, base_name):
        """Helper to find next available name like BASE_NAME_1, BASE_NAME_2, etc."""
        suffix = 1
        while True:
            potential_name = f"{base_name}_{suffix}"
            if not os.path.exists(os.path.join(project_custom_blocks_path, potential_name)):
                return potential_name
            suffix += 1

    def add_block_to_project(self, project_path, blueprint_key):
        # Requirement 2 & 4
        if blueprint_key not in self.available_blueprints:
            raise ValueError(f"Blueprint '{blueprint_key}' not found.")

        project_custom_blocks_path = os.path.join(project_path, CUSTOM_BLOCKS_DIR_NAME)
        os.makedirs(project_custom_blocks_path, exist_ok=True)

        # Requirement 4: Default naming with suffix
        custom_block_name = self._get_next_available_name_in_project(project_custom_blocks_path, blueprint_key)
        
        custom_block_folder_path = os.path.join(project_custom_blocks_path, custom_block_name)
        
        # Simulate copying from blueprint (mocked)
        # In a real scenario, this would copy from self.available_blueprints[blueprint_key]['path']
        os.makedirs(custom_block_folder_path, exist_ok=True) # Create the folder
        
        original_py_filename = blueprint_key + PYTHON_FILE_EXT
        new_py_filename = custom_block_name + PYTHON_FILE_EXT
        new_py_filepath = os.path.join(custom_block_folder_path, new_py_filename)

        # Simulate modifying Python file content (Requirement 4 & 5)
        # This is a highly simplified version. Real implementation needs robust parsing.
        blueprint_content = f"@atlasvibe_node\ndef {blueprint_key}(input1, input2):\n    # Original {blueprint_key} code\n    pass"
        modified_content = blueprint_content.replace(f"def {blueprint_key}", f"def {custom_block_name}")
        
        with open(new_py_filepath, "w") as f:
            f.write(modified_content)

        # Simulate creating/updating metadata (app.json, block_data.json, etc.)
        app_json_path = os.path.join(custom_block_folder_path, METADATA_APP_JSON)
        with open(app_json_path, "w") as f:
            json.dump({"name": custom_block_name, "key": custom_block_name, "original_blueprint": blueprint_key}, f)
        
        # ... create other files like block_data.json, example.md, test file ...
        # The test file should also be renamed and its content potentially updated.

        return {
            "name": custom_block_name,
            "path": custom_block_folder_path,
            "python_file": new_py_filename,
            "decorated_function_name": custom_block_name
        }

    def rename_custom_block(self, project_path, old_custom_block_name, new_potential_name_base):
        # Requirement 5
        project_custom_blocks_path = os.path.join(project_path, CUSTOM_BLOCKS_DIR_NAME)
        old_block_folder_path = os.path.join(project_custom_blocks_path, old_custom_block_name)

        if not os.path.exists(old_block_folder_path):
            raise FileNotFoundError(f"Custom block '{old_custom_block_name}' not found in project.")

        # Collision checks (Requirement 5)
        # 1. Check against blueprint names
        if new_potential_name_base in self.available_blueprints:
            final_new_name = self._get_next_available_name_in_project(project_custom_blocks_path, new_potential_name_base)
        # 2. Check against other existing custom block names (excluding itself if old_name is just base for suffix)
        elif os.path.exists(os.path.join(project_custom_blocks_path, new_potential_name_base)) and \
             new_potential_name_base != old_custom_block_name: # careful if old name is already suffixed
            final_new_name = self._get_next_available_name_in_project(project_custom_blocks_path, new_potential_name_base)
        else:
            # 3. Python symbol check (simplified for this mock - real check is complex)
            # For this mock, we assume if no direct folder collision, it's fine or gets suffixed.
            # A more robust check would involve parsing Python files in the project scope.
            # If new_potential_name_base is a common Python keyword, it should also be handled.
            # For now, if it's not a blueprint and not an existing folder, try it.
            # If it leads to a folder that exists, _get_next_available_name_in_project will suffix.
            if os.path.exists(os.path.join(project_custom_blocks_path, new_potential_name_base)):
                 final_new_name = self._get_next_available_name_in_project(project_custom_blocks_path, new_potential_name_base)
            else:
                 final_new_name = new_potential_name_base


        new_block_folder_path = os.path.join(project_custom_blocks_path, final_new_name)
        
        # Rename folder
        os.rename(old_block_folder_path, new_block_folder_path)
        
        # Rename .py file
        old_py_filename = old_custom_block_name + PYTHON_FILE_EXT
        new_py_filename = final_new_name + PYTHON_FILE_EXT
        os.rename(os.path.join(new_block_folder_path, old_py_filename), 
                  os.path.join(new_block_folder_path, new_py_filename))
        
        # Update Python code (decorated function name)
        py_filepath = os.path.join(new_block_folder_path, new_py_filename)
        with open(py_filepath, "r") as f:
            content = f.read()
        
        # This is a very simplified way to replace. Real implementation needs AST or careful regex.
        # It assumes the old function name was exactly old_custom_block_name.
        modified_content = content.replace(f"def {old_custom_block_name}", f"def {final_new_name}")
        # Also need to update @atlasvibe_node if it stored the name, or other references.
        
        with open(py_filepath, "w") as f:
            f.write(modified_content)
            
        # Update metadata files (app.json, etc.)
        app_json_path = os.path.join(new_block_folder_path, METADATA_APP_JSON)
        if os.path.exists(app_json_path):
            with open(app_json_path, "r") as f:
                app_data = json.load(f)
            app_data["name"] = final_new_name
            app_data["key"] = final_new_name
            with open(app_json_path, "w") as f:
                json.dump(app_data, f)
        
        # Rename test file and update its content (more complex)
        # ...

        return {"old_name": old_custom_block_name, "new_name": final_new_name, "path": new_block_folder_path}


# --- Test Fixtures ---
@pytest.fixture
def temp_project_dir(tmp_path):
    project_root = tmp_path / "TestProject1"
    project_root.mkdir()
    (project_root / CUSTOM_BLOCKS_DIR_NAME).mkdir()
    return str(project_root)

@pytest.fixture
def mock_blueprint_base_path(tmp_path):
    bp_dir = tmp_path / "mock_blueprints_ops"
    bp_dir.mkdir()
    
    # MATRIX_VIEW Blueprint
    matrix_view_bp = bp_dir / "MATRIX_VIEW"
    matrix_view_bp.mkdir()
    (matrix_view_bp / "MATRIX_VIEW.py").write_text(
        "# Original MATRIX_VIEW\n@atlasvibe_node\ndef MATRIX_VIEW(data):\n  return data"
    )
    (matrix_view_bp / METADATA_APP_JSON).write_text('{"name": "MATRIX_VIEW", "key": "MATRIX_VIEW"}')
    # ... other blueprint files ...
    
    return str(bp_dir)

@pytest.fixture
def block_service_instance(mock_blueprint_base_path):
    # This service instance will use the mocked blueprint path
    return MockBlockService(blueprint_base_path=mock_blueprint_base_path)


# --- Test Cases ---

def test_add_block_creates_custom_block_folder_and_files(block_service_instance, temp_project_dir):
    """
    Test Requirement 2: adding a new block to the flow will effectively create 
    new custom blocks inside the project folder.
    Also tests Requirement 4 for default naming (e.g., MATRIX_VIEW_1).
    """
    blueprint_key = "MATRIX_VIEW"
    
    # Action
    created_block_info = block_service_instance.add_block_to_project(temp_project_dir, blueprint_key)
    
    expected_custom_block_name = "MATRIX_VIEW_1" # First instance
    assert created_block_info["name"] == expected_custom_block_name
    
    custom_block_folder = os.path.join(temp_project_dir, CUSTOM_BLOCKS_DIR_NAME, expected_custom_block_name)
    assert os.path.isdir(custom_block_folder)
    
    # Check for renamed Python file
    expected_py_file = os.path.join(custom_block_folder, expected_custom_block_name + PYTHON_FILE_EXT)
    assert os.path.exists(expected_py_file)
    
    # Check Python file content for renamed function (simplified check)
    with open(expected_py_file, "r") as f:
        content = f.read()
        assert f"def {expected_custom_block_name}(" in content # Requirement 4
        assert f"@atlasvibe_node" in content

    # Check metadata (e.g., app.json)
    app_json_file = os.path.join(custom_block_folder, METADATA_APP_JSON)
    assert os.path.exists(app_json_file)
    with open(app_json_file, "r") as f:
        app_data = json.load(f)
        assert app_data["name"] == expected_custom_block_name
        assert app_data["key"] == expected_custom_block_name
        assert app_data["original_blueprint"] == blueprint_key

    # Test adding another instance of the same blueprint
    created_block_info_2 = block_service_instance.add_block_to_project(temp_project_dir, blueprint_key)
    expected_custom_block_name_2 = "MATRIX_VIEW_2" # Second instance
    assert created_block_info_2["name"] == expected_custom_block_name_2
    custom_block_folder_2 = os.path.join(temp_project_dir, CUSTOM_BLOCKS_DIR_NAME, expected_custom_block_name_2)
    assert os.path.isdir(custom_block_folder_2)


def test_gui_distinction_and_default_naming_backend_support(block_service_instance, temp_project_dir):
    """
    Test Requirement 4 (backend part): The name of blocks added from base blocks 
    will be by default the original block name + a number suffix.
    e.g., MATRIX_VIEW becomes MATRIX_VIEW_1.
    This is largely covered by test_add_block_creates_custom_block_folder_and_files.
    This test re-iterates the naming convention specifically.
    """
    # Add MATRIX_VIEW, should become MATRIX_VIEW_1
    info1 = block_service_instance.add_block_to_project(temp_project_dir, "MATRIX_VIEW")
    assert info1["name"] == "MATRIX_VIEW_1"
    assert info1["decorated_function_name"] == "MATRIX_VIEW_1"

    # Add another MATRIX_VIEW, should become MATRIX_VIEW_2
    info2 = block_service_instance.add_block_to_project(temp_project_dir, "MATRIX_VIEW")
    assert info2["name"] == "MATRIX_VIEW_2"
    assert info2["decorated_function_name"] == "MATRIX_VIEW_2"

    # Add a different block, e.g., ADD, should become ADD_1
    info_add = block_service_instance.add_block_to_project(temp_project_dir, "ADD")
    assert info_add["name"] == "ADD_1"
    assert info_add["decorated_function_name"] == "ADD_1"

    # Requirement 4 (GUI distinction):
    # This part ("distinction between base/default blocks and custom blocks disappeared from the GUI")
    # is primarily a frontend test.
    # A frontend test would:
    # 1. Mock the backend API that lists available blocks (blueprints).
    # 2. Simulate dragging a blueprint (e.g., "MATRIX_VIEW") onto the canvas.
    # 3. Verify that the node created on the canvas has the label "MATRIX_VIEW_1".
    # 4. Verify that the underlying block data points to a newly created custom block
    #    (e.g., its path is within the project's custom blocks directory).
    # 5. Verify that there's no separate UI section for "custom blocks" vs "standard blocks" when adding.
    # This requires UI testing tools and is not implemented here.
    pass


def test_rename_block_updates_folder_file_and_function_name(block_service_instance, temp_project_dir):
    """
    Test Requirement 5: renaming a block will be always possible, and it will 
    automatically rename the decorated function with the same name, updating 
    all the references in the code to the new name.
    """
    # Setup: Add an initial block
    initial_block_info = block_service_instance.add_block_to_project(temp_project_dir, "CONSTANT")
    old_name = initial_block_info["name"] # e.g., "CONSTANT_1"
    new_name_base = "MyRenamedConstant"

    # Action: Rename the block
    rename_info = block_service_instance.rename_custom_block(temp_project_dir, old_name, new_name_base)
    final_new_name = rename_info["new_name"] # Could be "MyRenamedConstant" or "MyRenamedConstant_1" if base collides

    # Assertions
    old_folder_path = os.path.join(temp_project_dir, CUSTOM_BLOCKS_DIR_NAME, old_name)
    new_folder_path = os.path.join(temp_project_dir, CUSTOM_BLOCKS_DIR_NAME, final_new_name)

    assert not os.path.exists(old_folder_path), "Old block folder should not exist after rename."
    assert os.path.isdir(new_folder_path), "New block folder was not created or not found."
    
    expected_py_file = os.path.join(new_folder_path, final_new_name + PYTHON_FILE_EXT)
    assert os.path.exists(expected_py_file), ".py file was not renamed or not found in new folder."

    with open(expected_py_file, "r") as f:
        content = f.read()
        assert f"def {final_new_name}(" in content, "Decorated function name was not updated in .py file."
        assert f"def {old_name}(" not in content, "Old function name should not exist in .py file."

    app_json_file = os.path.join(new_folder_path, METADATA_APP_JSON)
    assert os.path.exists(app_json_file)
    with open(app_json_file, "r") as f:
        app_data = json.load(f)
        assert app_data["name"] == final_new_name
        assert app_data["key"] == final_new_name

    # Note: "updating all the references in the code to the new name" is a very complex task
    # if it means updating other Python files that might import/use this block.
    # The current mock only renames the function definition within its own file.
    # A full implementation would require extensive static analysis (e.g., AST parsing)
    # of the entire project, which is a significant feature. This test covers the local rename.


def test_rename_block_handles_collision_with_blueprint_name(block_service_instance, temp_project_dir):
    """
    Test Req 5: Collision check - new name is a blueprint name.
    """
    initial_block = block_service_instance.add_block_to_project(temp_project_dir, "CONSTANT") # CONSTANT_1
    
    # Try to rename to "MATRIX_VIEW", which is a blueprint name.
    # Expect it to become "MATRIX_VIEW_1" (or _2 if MATRIX_VIEW_1 already exists as custom).
    rename_info = block_service_instance.rename_custom_block(temp_project_dir, initial_block["name"], "MATRIX_VIEW")
    
    # Check if the name was suffixed
    assert rename_info["new_name"].startswith("MATRIX_VIEW_")
    assert rename_info["new_name"] != "MATRIX_VIEW" 
    
    new_folder_path = os.path.join(temp_project_dir, CUSTOM_BLOCKS_DIR_NAME, rename_info["new_name"])
    assert os.path.isdir(new_folder_path)


def test_rename_block_handles_collision_with_existing_custom_block(block_service_instance, temp_project_dir):
    """
    Test Req 5: Collision check - new name matches another custom block.
    """
    block1 = block_service_instance.add_block_to_project(temp_project_dir, "CONSTANT") # CONSTANT_1
    block2 = block_service_instance.add_block_to_project(temp_project_dir, "ADD")      # ADD_1
    
    # Try to rename block2 (ADD_1) to "CONSTANT_1" (which is block1's name)
    rename_info = block_service_instance.rename_custom_block(temp_project_dir, block2["name"], "CONSTANT_1")
    
    # Expect it to be suffixed, e.g., "CONSTANT_1_1" or "CONSTANT_2" if that's how the suffix logic works
    assert rename_info["new_name"] != "CONSTANT_1"
    assert rename_info["new_name"].startswith("CONSTANT_") # or CONSTANT_1_

    new_folder_path = os.path.join(temp_project_dir, CUSTOM_BLOCKS_DIR_NAME, rename_info["new_name"])
    assert os.path.isdir(new_folder_path)


def test_rename_block_handles_python_symbol_collision_simplified(block_service_instance, temp_project_dir):
    """
    Test Req 5: Collision check - new name is a Python keyword/problematic symbol (simplified).
    A full Python symbol collision check is very complex (AST parsing of project).
    This test can check for a predefined list of problematic names or rely on suffixing for safety.
    The current MockBlockService's rename logic will try the name, and if it leads to an existing
    folder (even if not a block, but just a folder with that name), it will suffix.
    """
    initial_block = block_service_instance.add_block_to_project(temp_project_dir, "CONSTANT") # CONSTANT_1
    
    # For this mock, let's assume "pass" is a problematic name that might exist as a folder
    # or is a keyword we want to avoid as a direct block name.
    # Create a dummy folder to simulate a collision that's not a blueprint or existing block.
    os.makedirs(os.path.join(temp_project_dir, CUSTOM_BLOCKS_DIR_NAME, "pass"), exist_ok=True)

    rename_info = block_service_instance.rename_custom_block(temp_project_dir, initial_block["name"], "pass")
    
    assert rename_info["new_name"].startswith("pass_") # Expect suffixing
    assert rename_info["new_name"] != "pass"
    
    new_folder_path = os.path.join(temp_project_dir, CUSTOM_BLOCKS_DIR_NAME, rename_info["new_name"])
    assert os.path.isdir(new_folder_path)


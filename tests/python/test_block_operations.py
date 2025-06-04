# Copyright (c) 2024 Emasoft (for atlasvibe modifications and derivative work)
# Copyright (c) 2024 Atlasvibe (for the original "Atlasvibe Studio" software)
#
# This software is licensed under the MIT License.
# Refer to the LICENSE file for more details.

import pytest
import os
import shutil
import json
from unittest.mock import patch, MagicMock, call
from pathlib import Path 

from . import constants
from .mocks import MockBlockService


# --- Test Fixtures ---
# temp_project_dir is now sourced from conftest.py

@pytest.fixture
def mock_blueprint_base_path(tmp_path: Path) -> Path: 
    bp_dir = tmp_path / "mock_blueprints_ops"
    bp_dir.mkdir(parents=True, exist_ok=True)
    
    # MATRIX_VIEW Blueprint
    matrix_view_bp = bp_dir / constants.BLUEPRINT_MATRIX_VIEW
    matrix_view_bp.mkdir()
    (matrix_view_bp / (constants.BLUEPRINT_MATRIX_VIEW + constants.PYTHON_FILE_EXT)).write_text(
        f"# Original {constants.BLUEPRINT_MATRIX_VIEW}\n@atlasvibe_node\ndef {constants.BLUEPRINT_MATRIX_VIEW}(data):\n  return data"
    )
    (matrix_view_bp / constants.METADATA_APP_JSON).write_text(f'{{"name": "{constants.BLUEPRINT_MATRIX_VIEW}", "key": "{constants.BLUEPRINT_MATRIX_VIEW}"}}')

    # ADD Blueprint
    add_bp = bp_dir / constants.BLUEPRINT_ADD
    add_bp.mkdir()
    (add_bp / (constants.BLUEPRINT_ADD + constants.PYTHON_FILE_EXT)).write_text(
        f"@atlasvibe_node\ndef {constants.BLUEPRINT_ADD}(a, b):\n  return a + b"
    )
    (add_bp / constants.METADATA_APP_JSON).write_text(f'{{"name": "{constants.BLUEPRINT_ADD}", "key": "{constants.BLUEPRINT_ADD}"}}')

    # CONSTANT Blueprint
    constant_bp = bp_dir / constants.BLUEPRINT_CONSTANT
    constant_bp.mkdir()
    (constant_bp / (constants.BLUEPRINT_CONSTANT + constants.PYTHON_FILE_EXT)).write_text(
        f"@atlasvibe_node\ndef {constants.BLUEPRINT_CONSTANT}():\n  return 123"
    )
    (constant_bp / constants.METADATA_APP_JSON).write_text(f'{{"name": "{constants.BLUEPRINT_CONSTANT}", "key": "{constants.BLUEPRINT_CONSTANT}"}}')
    
    # Another blueprint for varied testing
    another_bp = bp_dir / "ANOTHER_NODE"
    another_bp.mkdir()
    (another_bp / ("ANOTHER_NODE" + constants.PYTHON_FILE_EXT)).write_text(
        "@atlasvibe_node\ndef ANOTHER_NODE():\n  return 'another'"
    )
    (another_bp / constants.METADATA_APP_JSON).write_text('{"name": "ANOTHER_NODE", "key": "ANOTHER_NODE"}')


    return bp_dir

@pytest.fixture
def block_service_instance(mock_blueprint_base_path: Path): 
    return MockBlockService(blueprint_base_path=mock_blueprint_base_path)


# --- Test Cases ---

def test_add_block_creates_custom_block_folder_and_files(block_service_instance: MockBlockService, temp_project_dir: Path):
    """
    Test Requirement 2: adding a new block to the flow will effectively create 
    new custom blocks inside the project folder.
    Also tests Requirement 4 for default naming.
    """
    blueprint_key = constants.BLUEPRINT_MATRIX_VIEW
    project_path_str = str(temp_project_dir) 
    
    created_block_info = block_service_instance.add_block_to_project(project_path_str, blueprint_key)
    
    expected_custom_block_name = f"{constants.BLUEPRINT_MATRIX_VIEW}_1"
    assert created_block_info["name"] == expected_custom_block_name
    
    custom_block_folder = os.path.join(project_path_str, constants.CUSTOM_BLOCKS_DIR_NAME, expected_custom_block_name)
    assert os.path.isdir(custom_block_folder)
    
    expected_py_file = os.path.join(custom_block_folder, expected_custom_block_name + constants.PYTHON_FILE_EXT)
    assert os.path.exists(expected_py_file)
    
    with open(expected_py_file, "r") as f:
        content = f.read()
        assert f"def {expected_custom_block_name}(" in content 
        assert "@atlasvibe_node" in content
        assert f"# Original {constants.BLUEPRINT_MATRIX_VIEW}" in content

    app_json_file = os.path.join(custom_block_folder, constants.METADATA_APP_JSON)
    assert os.path.exists(app_json_file)
    with open(app_json_file, "r") as f:
        app_data = json.load(f)
        assert app_data["name"] == expected_custom_block_name
        assert app_data["key"] == expected_custom_block_name
        assert app_data["original_blueprint"] == blueprint_key

    created_block_info_2 = block_service_instance.add_block_to_project(project_path_str, blueprint_key)
    expected_custom_block_name_2 = f"{constants.BLUEPRINT_MATRIX_VIEW}_2"
    assert created_block_info_2["name"] == expected_custom_block_name_2
    custom_block_folder_2 = os.path.join(project_path_str, constants.CUSTOM_BLOCKS_DIR_NAME, expected_custom_block_name_2)
    assert os.path.isdir(custom_block_folder_2)


def test_gui_distinction_and_default_naming_backend_support(block_service_instance: MockBlockService, temp_project_dir: Path):
    """
    Test Requirement 4 (backend part): The name of blocks added from base blocks 
    will be by default the original block name + a number suffix.
    """
    project_path_str = str(temp_project_dir)
    
    info1 = block_service_instance.add_block_to_project(project_path_str, constants.BLUEPRINT_MATRIX_VIEW)
    assert info1["name"] == f"{constants.BLUEPRINT_MATRIX_VIEW}_1"
    assert info1["decorated_function_name"] == f"{constants.BLUEPRINT_MATRIX_VIEW}_1"

    info2 = block_service_instance.add_block_to_project(project_path_str, constants.BLUEPRINT_MATRIX_VIEW)
    assert info2["name"] == f"{constants.BLUEPRINT_MATRIX_VIEW}_2"
    assert info2["decorated_function_name"] == f"{constants.BLUEPRINT_MATRIX_VIEW}_2"

    info_add = block_service_instance.add_block_to_project(project_path_str, constants.BLUEPRINT_ADD)
    assert info_add["name"] == f"{constants.BLUEPRINT_ADD}_1"
    assert info_add["decorated_function_name"] == f"{constants.BLUEPRINT_ADD}_1"
    pass


def test_rename_block_updates_folder_file_and_function_name(block_service_instance: MockBlockService, temp_project_dir: Path):
    """
    Test Requirement 5: renaming a block will be always possible, and it will 
    automatically rename the decorated function with the same name.
    """
    project_path_str = str(temp_project_dir)
    initial_block_info = block_service_instance.add_block_to_project(project_path_str, constants.BLUEPRINT_CONSTANT)
    old_name = initial_block_info["name"] 
    new_name_base = "MyRenamedConstant"

    rename_info = block_service_instance.rename_custom_block(project_path_str, old_name, new_name_base)
    final_new_name = rename_info["new_name"]
    assert final_new_name == new_name_base # Expecting it to take the new name directly

    old_folder_path = os.path.join(project_path_str, constants.CUSTOM_BLOCKS_DIR_NAME, old_name)
    new_folder_path = os.path.join(project_path_str, constants.CUSTOM_BLOCKS_DIR_NAME, final_new_name)

    assert not os.path.exists(old_folder_path), "Old block folder should not exist after rename."
    assert os.path.isdir(new_folder_path), "New block folder was not created or not found."
    
    expected_py_file = os.path.join(new_folder_path, final_new_name + constants.PYTHON_FILE_EXT)
    assert os.path.exists(expected_py_file), ".py file was not renamed or not found in new folder."

    with open(expected_py_file, "r") as f:
        content = f.read()
        assert f"def {final_new_name}(" in content, "Decorated function name was not updated in .py file."
        assert f"def {old_name}(" not in content, "Old function name should not exist in .py file."

    app_json_file = os.path.join(new_folder_path, constants.METADATA_APP_JSON)
    assert os.path.exists(app_json_file)
    with open(app_json_file, "r") as f:
        app_data = json.load(f)
        assert app_data["name"] == final_new_name
        assert app_data["key"] == final_new_name


def test_rename_block_to_its_current_name(block_service_instance: MockBlockService, temp_project_dir: Path):
    """Test renaming a block to its current name results in no change."""
    project_path_str = str(temp_project_dir)
    initial_block_info = block_service_instance.add_block_to_project(project_path_str, constants.BLUEPRINT_CONSTANT)
    current_name = initial_block_info["name"] # e.g., CONSTANT_1

    rename_info = block_service_instance.rename_custom_block(project_path_str, current_name, current_name)
    
    assert rename_info["new_name"] == current_name
    original_folder_path = os.path.join(project_path_str, constants.CUSTOM_BLOCKS_DIR_NAME, current_name)
    assert os.path.isdir(original_folder_path) # Folder should still be there
    # Verify content of python file still has current_name
    py_file = os.path.join(original_folder_path, current_name + constants.PYTHON_FILE_EXT)
    with open(py_file, "r") as f:
        content = f.read()
        assert f"def {current_name}(" in content


def test_rename_block_to_its_base_name_when_available(block_service_instance: MockBlockService, temp_project_dir: Path):
    """Test renaming 'BLOCK_1' to 'BLOCK' when 'BLOCK' is available or a blueprint."""
    project_path_str = str(temp_project_dir)
    
    # Case 1: Renaming "ANOTHER_NODE_1" to "ANOTHER_NODE" (which is a blueprint key)
    initial_block_info_1 = block_service_instance.add_block_to_project(project_path_str, "ANOTHER_NODE") # Creates ANOTHER_NODE_1
    old_name_1 = initial_block_info_1["name"] # ANOTHER_NODE_1
    new_base_name_1 = "ANOTHER_NODE" 

    rename_info_1 = block_service_instance.rename_custom_block(project_path_str, old_name_1, new_base_name_1)
    # Expected: Since "ANOTHER_NODE" is a blueprint, it should be suffixed.
    # As "ANOTHER_NODE_1" is being renamed (so it's available), the result should be "ANOTHER_NODE_1".
    assert rename_info_1["new_name"] == "ANOTHER_NODE_1"
    new_folder_path_1 = os.path.join(project_path_str, constants.CUSTOM_BLOCKS_DIR_NAME, "ANOTHER_NODE_1")
    assert os.path.isdir(new_folder_path_1)

    # Case 2: Renaming "CONSTANT_1" to "MyUniqueBase" (which is not a blueprint and available)
    initial_block_info_2 = block_service_instance.add_block_to_project(project_path_str, constants.BLUEPRINT_CONSTANT) # Creates CONSTANT_1
    old_name_2 = initial_block_info_2["name"] # CONSTANT_1
    new_available_base_name = "MyUniqueBase"

    rename_info_2 = block_service_instance.rename_custom_block(project_path_str, old_name_2, new_available_base_name)
    assert rename_info_2["new_name"] == new_available_base_name
    new_folder_path_2 = os.path.join(project_path_str, constants.CUSTOM_BLOCKS_DIR_NAME, new_available_base_name)
    assert os.path.isdir(new_folder_path_2)


def test_rename_block_handles_collision_with_blueprint_name(block_service_instance: MockBlockService, temp_project_dir: Path):
    """Test Req 5: Collision check - new name is a blueprint name."""
    project_path_str = str(temp_project_dir)
    initial_block = block_service_instance.add_block_to_project(project_path_str, constants.BLUEPRINT_CONSTANT) # CONSTANT_1
    
    # Add MATRIX_VIEW_1 to make MATRIX_VIEW_1 taken
    block_service_instance.add_block_to_project(project_path_str, constants.BLUEPRINT_MATRIX_VIEW)


    rename_info = block_service_instance.rename_custom_block(project_path_str, initial_block["name"], constants.BLUEPRINT_MATRIX_VIEW)
    
    # Expect MATRIX_VIEW_2 because MATRIX_VIEW is a blueprint and MATRIX_VIEW_1 is already taken
    assert rename_info["new_name"] == f"{constants.BLUEPRINT_MATRIX_VIEW}_2" 
    
    new_folder_path = os.path.join(project_path_str, constants.CUSTOM_BLOCKS_DIR_NAME, rename_info["new_name"])
    assert os.path.isdir(new_folder_path)


def test_rename_block_handles_collision_with_existing_custom_block(block_service_instance: MockBlockService, temp_project_dir: Path):
    """Test Req 5: Collision check - new name matches another custom block."""
    project_path_str = str(temp_project_dir)
    # block1 will be CONSTANT_1
    block1 = block_service_instance.add_block_to_project(project_path_str, constants.BLUEPRINT_CONSTANT)
    # block2 will be ADD_1
    block2 = block_service_instance.add_block_to_project(project_path_str, constants.BLUEPRINT_ADD)
    
    # Try to rename block2 (ADD_1) to "CONSTANT_1" (which is block1's name)
    rename_info = block_service_instance.rename_custom_block(project_path_str, block2["name"], block1["name"])
    
    # Expect it to be suffixed, e.g., "CONSTANT_1_1"
    assert rename_info["new_name"] != block1["name"]
    assert rename_info["new_name"].startswith(f"{block1['name']}_") # e.g. CONSTANT_1_1

    new_folder_path = os.path.join(project_path_str, constants.CUSTOM_BLOCKS_DIR_NAME, rename_info["new_name"])
    assert os.path.isdir(new_folder_path)


def test_rename_block_handles_python_symbol_collision_simplified(block_service_instance: MockBlockService, temp_project_dir: Path):
    """
    Test Req 5: Collision check - new name is a Python keyword/problematic symbol (simplified by folder existing).
    """
    project_path_str = str(temp_project_dir)
    initial_block = block_service_instance.add_block_to_project(project_path_str, constants.BLUEPRINT_CONSTANT) 
    
    problematic_name = "pass" # Not a blueprint, assume not an existing custom block initially
    # Simulate a collision by creating a folder with this problematic name
    os.makedirs(os.path.join(project_path_str, constants.CUSTOM_BLOCKS_DIR_NAME, problematic_name), exist_ok=True)

    rename_info = block_service_instance.rename_custom_block(project_path_str, initial_block["name"], problematic_name)
    
    # Expect suffixing because 'pass' folder exists
    assert rename_info["new_name"].startswith(f"{problematic_name}_") 
    assert rename_info["new_name"] != problematic_name
    
    new_folder_path = os.path.join(project_path_str, constants.CUSTOM_BLOCKS_DIR_NAME, rename_info["new_name"])
    assert os.path.isdir(new_folder_path)


def test_add_block_with_target_name_collision(block_service_instance: MockBlockService, temp_project_dir: Path):
    """Test add_block_to_project with target_custom_block_name that already exists."""
    project_path_str = str(temp_project_dir)
    existing_block_name = f"{constants.BLUEPRINT_CONSTANT}_1"
    block_service_instance.add_block_to_project(project_path_str, constants.BLUEPRINT_CONSTANT) # Creates CONSTANT_1

    # Try to add another block but suggest the colliding name
    # The mock's add_block_to_project currently ignores target_custom_block_name if it collides,
    # and generates a new suffixed name based on blueprint_key.
    created_info = block_service_instance.add_block_to_project(
        project_path_str, 
        constants.BLUEPRINT_ADD, # Different blueprint
        target_custom_block_name=existing_block_name # Suggesting CONSTANT_1
    )
    # Expected: ADD_1 (or ADD_X), NOT CONSTANT_1 or an error.
    # Based on current mock: it will generate ADD_1 because target_custom_block_name logic in add_block_to_project
    # is simplified to fall back to blueprint_key based suffixing if target name exists.
    assert created_info["name"] != existing_block_name
    assert created_info["name"].startswith(constants.BLUEPRINT_ADD + "_")


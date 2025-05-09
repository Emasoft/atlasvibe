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


def test_rename_block_handles_collision_with_blueprint_name(block_service_instance: MockBlockService, temp_project_dir: Path):
    """
    Test Req 5: Collision check - new name is a blueprint name.
    """
    project_path_str = str(temp_project_dir)
    initial_block = block_service_instance.add_block_to_project(project_path_str, constants.BLUEPRINT_CONSTANT) 
    
    rename_info = block_service_instance.rename_custom_block(project_path_str, initial_block["name"], constants.BLUEPRINT_MATRIX_VIEW)
    
    assert rename_info["new_name"].startswith(f"{constants.BLUEPRINT_MATRIX_VIEW}_")
    assert rename_info["new_name"] != constants.BLUEPRINT_MATRIX_VIEW 
    
    new_folder_path = os.path.join(project_path_str, constants.CUSTOM_BLOCKS_DIR_NAME, rename_info["new_name"])
    assert os.path.isdir(new_folder_path)


def test_rename_block_handles_collision_with_existing_custom_block(block_service_instance: MockBlockService, temp_project_dir: Path):
    """
    Test Req 5: Collision check - new name matches another custom block.
    """
    project_path_str = str(temp_project_dir)
    block1 = block_service_instance.add_block_to_project(project_path_str, constants.BLUEPRINT_CONSTANT) # e.g. CONSTANT_1
    block2 = block_service_instance.add_block_to_project(project_path_str, constants.BLUEPRINT_ADD)      # e.g. ADD_1
    
    # Try to rename block2 (e.g. ADD_1) to block1's name (e.g. CONSTANT_1)
    rename_info = block_service_instance.rename_custom_block(project_path_str, block2["name"], block1["name"])
    
    assert rename_info["new_name"] != block1["name"]
    assert rename_info["new_name"].startswith(f"{block1['name']}_")

    new_folder_path = os.path.join(project_path_str, constants.CUSTOM_BLOCKS_DIR_NAME, rename_info["new_name"])
    assert os.path.isdir(new_folder_path)


def test_rename_block_handles_python_symbol_collision_simplified(block_service_instance: MockBlockService, temp_project_dir: Path):
    """
    Test Req 5: Collision check - new name is a Python keyword/problematic symbol (simplified).
    """
    project_path_str = str(temp_project_dir)
    initial_block = block_service_instance.add_block_to_project(project_path_str, constants.BLUEPRINT_CONSTANT) 
    
    problematic_name = "pass"
    # Simulate a collision by creating a folder with this problematic name
    os.makedirs(os.path.join(project_path_str, constants.CUSTOM_BLOCKS_DIR_NAME, problematic_name), exist_ok=True)

    rename_info = block_service_instance.rename_custom_block(project_path_str, initial_block["name"], problematic_name)
    
    assert rename_info["new_name"].startswith(f"{problematic_name}_") 
    assert rename_info["new_name"] != problematic_name
    
    new_folder_path = os.path.join(project_path_str, constants.CUSTOM_BLOCKS_DIR_NAME, rename_info["new_name"])
    assert os.path.isdir(new_folder_path)


# Copyright (c) 2024 Emasoft (for atlasvibe modifications and derivative work)
# Copyright (c) 2024 Flojoy (for the original "Flojoy Studio" software)
#
# This software is licensed under the MIT License.
# Refer to the LICENSE file for more details.

import pytest
import os
import shutil
from unittest.mock import patch, MagicMock, call
from pathlib import Path

from . import constants
from .mocks import MockProjectService, MockBlockService


# --- Test Fixtures ---
# temp_project_base_dir is sourced from conftest.py
# mock_blueprint_dir is sourced from conftest.py

@pytest.fixture
def project_service_instance():
    return MockProjectService()

@pytest.fixture
def block_service_instance(mock_blueprint_dir: Path): # mock_blueprint_dir from conftest.py
    # This instance of MockBlockService will use the blueprints created by mock_blueprint_dir
    return MockBlockService(blueprint_base_path=mock_blueprint_dir)


# --- Test Cases ---

def test_create_new_project_creates_folder_structure(project_service_instance, temp_project_base_dir):
    """
    Test Requirement 1: creating a new project will also create a new folder 
    with the name of the project and a subfolder for custom blocks.
    """
    project_name = "MyNewTestProject"
    base_path_str = str(temp_project_base_dir) 
    
    created_project_path = project_service_instance.create_new_project(project_name, base_path_str)
    
    expected_project_path = os.path.join(base_path_str, project_name)
    expected_custom_blocks_path = os.path.join(expected_project_path, constants.CUSTOM_BLOCKS_DIR_NAME)
    
    assert created_project_path == expected_project_path
    assert os.path.isdir(expected_project_path), "Project directory was not created."
    assert os.path.isdir(expected_custom_blocks_path), f"'{constants.CUSTOM_BLOCKS_DIR_NAME}' subdirectory was not created."


@patch('os.path.exists') # May need to be more selective or remove if using real file checks with tmp_path
@patch('os.makedirs')   # May need to be more selective or remove
@patch('shutil.copytree') 
@patch('builtins.open', new_callable=MagicMock) 
def test_project_template_creates_custom_blocks(
    mock_open, mock_copytree, mock_makedirs, mock_path_exists, # These mocks might interfere with MockBlockService's own file ops
    project_service_instance: MockProjectService, 
    block_service_instance: MockBlockService, # This is now the shared mock
    temp_project_base_dir: Path, 
    mock_blueprint_dir: Path # Used by block_service_instance fixture
):
    """
    Test Requirement 3: when selecting a new project template to start a new project, 
    the default blocks of the template are actually created as custom blocks 
    inside the project folder.
    """
    template_name = "BasicTemplate" 
    new_project_name = "ProjectFromBasicTemplate"
    base_path_str = str(temp_project_base_dir)

    # Unpatch os.makedirs for the actual service calls if they are to create dirs
    # This test becomes more of an integration test if mocks for os are removed.
    # For now, assume the mocks are for external dependencies not part of the service's direct logic.
    # The MockBlockService itself performs os.makedirs, os.path.exists.
    # If we are testing the MockProjectService's interaction with MockBlockService,
    # we might not need to mock os.path.exists and os.makedirs globally here.
    # Let's assume the mocks are for other things, and let MockBlockService do its work.
    # This test might need refinement based on what exactly is being unit-tested vs integrated.

    # Spy on the add_block_to_project method of the already instantiated mock service
    block_service_instance.add_block_to_project = MagicMock(
        wraps=block_service_instance.add_block_to_project
    )
    
    # Action
    project_path, created_blocks_details = project_service_instance.create_project_from_template(
        template_name, new_project_name, base_path_str, block_service_instance
    )

    expected_project_path = os.path.join(base_path_str, new_project_name)
    # These assertions rely on the MockProjectService and MockBlockService actually creating directories
    assert os.path.isdir(expected_project_path) 
    assert os.path.isdir(os.path.join(expected_project_path, constants.CUSTOM_BLOCKS_DIR_NAME))

    expected_blueprint_keys = [
        constants.BLUEPRINT_INPUT_NODE, 
        constants.BLUEPRINT_PROCESSING_NODE, 
        constants.BLUEPRINT_OUTPUT_NODE
    ]
    
    assert block_service_instance.add_block_to_project.call_count == len(expected_blueprint_keys)

    created_block_names = [details['name'] for details in created_blocks_details]

    for bp_key in expected_blueprint_keys:
        expected_custom_name = f"{bp_key}_1" 
        assert expected_custom_name in created_block_names
        
        block_detail = next(b for b in created_blocks_details if b['name'] == expected_custom_name)
        custom_block_folder = os.path.join(expected_project_path, constants.CUSTOM_BLOCKS_DIR_NAME, expected_custom_name)
        assert os.path.isdir(custom_block_folder) 
        
        py_file = os.path.join(custom_block_folder, expected_custom_name + constants.PYTHON_FILE_EXT)
        assert os.path.exists(py_file)
        
        app_json_path = os.path.join(custom_block_folder, constants.METADATA_APP_JSON)
        assert os.path.exists(app_json_path)

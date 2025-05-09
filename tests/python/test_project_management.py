# Copyright (c) 2024 Emasoft (for atlasvibe modifications and derivative work)
# Copyright (c) 2024 Flojoy (for the original "Flojoy Studio" software)
#
# This software is licensed under the MIT License.
# Refer to the LICENSE file for more details.

import pytest
import os
import shutil
from unittest.mock import patch, MagicMock, call

# Hypothetical service modules - these would need to be implemented
# from atlasvibe_engine import project_service, block_service, constants

# For now, let's define placeholder constants if not available from a module
# In a real scenario, these would come from your application's constants module
CUSTOM_BLOCKS_DIR_NAME = "atlasvibe_custom_blocks"
PYTHON_FILE_EXT = ".py"
METADATA_APP_JSON = "app.json"
METADATA_BLOCK_DATA_JSON = "block_data.json"
METADATA_EXAMPLE_MD = "example.md"
TEST_FILE_SUFFIX = "_test_.py"


# Placeholder for services - In a real app, these would be imported
class MockProjectService:
    def create_new_project(self, project_name, base_path):
        # This function needs to be implemented
        # It should create a directory for the project and
        # a subdirectory for custom blocks.
        project_path = os.path.join(base_path, project_name)
        custom_blocks_path = os.path.join(project_path, CUSTOM_BLOCKS_DIR_NAME)
        os.makedirs(custom_blocks_path, exist_ok=True)
        return project_path

    def create_project_from_template(self, template_name, new_project_name, base_path, block_service_instance):
        # This function needs to be implemented
        # 1. Create the project folder structure (similar to create_new_project)
        # 2. Get the template definition (e.g., list of blueprint blocks and their connections)
        # 3. For each block in the template:
        #    a. Determine the correct new custom block name (e.g., BLUEPRINT_NAME_1, BLUEPRINT_NAME_2)
        #    b. Call block_service_instance.add_block_to_project to create it as a custom block
        #    c. Store/update metadata and connection information.
        project_path = self.create_new_project(new_project_name, base_path)

        # --- Mocked template definition ---
        mock_template_blocks = []
        if template_name == "BasicTemplate":
            mock_template_blocks = [
                {"blueprint_key": "INPUT_NODE", "id_in_template": "input1"},
                {"blueprint_key": "PROCESSING_NODE", "id_in_template": "proc1"},
                {"blueprint_key": "OUTPUT_NODE", "id_in_template": "out1"}
            ]
        # --- End Mocked template definition ---

        created_block_details = []
        for i, block_def in enumerate(mock_template_blocks):
            # In a real implementation, get_next_available_block_name would be more robust
            # and part of block_service or project_service
            block_base_name = block_def["blueprint_key"]
            # Simplified naming for the test; real implementation needs robust unique name generation
            # This part directly relates to Requirement 4 for default naming.
            # We'd need a way to track existing names in the project to find the next suffix.
            # For this test, we'll assume block_service.add_block_to_project handles unique suffixed naming.
            
            # The add_block_to_project should handle the "_1", "_2" suffixing.
            # We pass the base blueprint key.
            created_block_info = block_service_instance.add_block_to_project(
                project_path=project_path,
                blueprint_key=block_def["blueprint_key"],
                # target_custom_block_name is determined by add_block_to_project
            )
            created_block_details.append(created_block_info)
        
        # Here, you would also handle connections based on the template
        # and update any project-level metadata.
        return project_path, created_block_details


class MockBlockService:
    def add_block_to_project(self, project_path, blueprint_key, target_custom_block_name=None):
        # This function needs to be implemented based on Requirement 2 & 4
        # 1. Determine the actual target_custom_block_name (e.g., blueprint_key_1, blueprint_key_2)
        #    by checking existing blocks in project_path/CUSTOM_BLOCKS_DIR_NAME
        # 2. Create the custom block folder: project_path/CUSTOM_BLOCKS_DIR_NAME/actual_target_custom_block_name
        # 3. Copy blueprint files (e.g., from a predefined blueprint path)
        # 4. Rename the .py file and the test file.
        # 5. Modify the @atlasvibe_node decorated function name in the .py file.
        # 6. Update metadata files (app.json, block_data.json)
        
        # Simplified unique name generation for testing (Requirement 4)
        custom_blocks_path = os.path.join(project_path, CUSTOM_BLOCKS_DIR_NAME)
        os.makedirs(custom_blocks_path, exist_ok=True) # Ensure dir exists
        
        suffix = 1
        if target_custom_block_name: # If a name is suggested (e.g. by rename)
             final_block_name = target_custom_block_name
        else: # Generate default name like BLUEPRINT_KEY_1
            while True:
                final_block_name = f"{blueprint_key}_{suffix}"
                if not os.path.exists(os.path.join(custom_blocks_path, final_block_name)):
                    break
                suffix += 1

        new_block_folder_path = os.path.join(custom_blocks_path, final_block_name)
        os.makedirs(new_block_folder_path, exist_ok=True)

        # Simulate creating files
        py_file_name = final_block_name + PYTHON_FILE_EXT
        test_file_name = final_block_name + TEST_FILE_SUFFIX
        
        # Mock blueprint path
        mock_blueprint_path = f"/mock_blueprints/{blueprint_key}"

        # Simulate copying and renaming (very simplified)
        # In reality, you'd copy from mock_blueprint_path/blueprint_key.py
        with open(os.path.join(new_block_folder_path, py_file_name), "w") as f:
            f.write(f"# Original blueprint: {blueprint_key}\n")
            f.write(f"@atlasvibe_node\n")
            f.write(f"def {final_block_name}(param1):\n") # Requirement 4 & 5
            f.write(f"    pass\n")
        
        with open(os.path.join(new_block_folder_path, METADATA_APP_JSON), "w") as f:
            f.write(f'{{"name": "{final_block_name}", "key": "{final_block_name}"}}') # Requirement 3 & 4
        
        # ... create other files like block_data.json, example.md, test file ...

        return {
            "name": final_block_name, 
            "path": new_block_folder_path,
            "python_file": py_file_name,
            "decorated_function_name": final_block_name # Requirement 4
        }

    def get_blueprints(self): # Mock
        return {"INPUT_NODE": {}, "PROCESSING_NODE": {}, "OUTPUT_NODE": {}}


# --- Test Fixtures ---
@pytest.fixture
def temp_project_base_dir():
    temp_dir = "temp_test_projects"
    os.makedirs(temp_dir, exist_ok=True)
    yield temp_dir
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)

@pytest.fixture
def project_service_instance():
    return MockProjectService()

@pytest.fixture
def block_service_instance():
    return MockBlockService()

@pytest.fixture
def mock_blueprint_dir(tmp_path):
    bp_dir = tmp_path / "mock_blueprints"
    bp_dir.mkdir()
    
    # Create a mock INPUT_NODE blueprint
    input_node_bp = bp_dir / "INPUT_NODE"
    input_node_bp.mkdir()
    (input_node_bp / "INPUT_NODE.py").write_text("@atlasvibe_node\ndef INPUT_NODE(): pass")
    (input_node_bp / METADATA_APP_JSON).write_text('{"name": "INPUT_NODE", "key": "INPUT_NODE"}')

    # Create a mock PROCESSING_NODE blueprint
    proc_node_bp = bp_dir / "PROCESSING_NODE"
    proc_node_bp.mkdir()
    (proc_node_bp / "PROCESSING_NODE.py").write_text("@atlasvibe_node\ndef PROCESSING_NODE(input): pass")
    (proc_node_bp / METADATA_APP_JSON).write_text('{"name": "PROCESSING_NODE", "key": "PROCESSING_NODE"}')

    # Create a mock OUTPUT_NODE blueprint
    output_node_bp = bp_dir / "OUTPUT_NODE"
    output_node_bp.mkdir()
    (output_node_bp / "OUTPUT_NODE.py").write_text("@atlasvibe_node\ndef OUTPUT_NODE(input): pass")
    (output_node_bp / METADATA_APP_JSON).write_text('{"name": "OUTPUT_NODE", "key": "OUTPUT_NODE"}')
    
    return str(bp_dir)


# --- Test Cases ---

def test_create_new_project_creates_folder_structure(project_service_instance, temp_project_base_dir):
    """
    Test Requirement 1: creating a new project will also create a new folder 
    with the name of the project and a subfolder for custom blocks.
    """
    project_name = "MyNewTestProject"
    
    # Action: Call the (to be implemented) service function
    # For TDD, we assume project_service.create_new_project exists and call it.
    # The actual implementation of create_new_project will make this test pass.
    created_project_path = project_service_instance.create_new_project(project_name, temp_project_base_dir)
    
    expected_project_path = os.path.join(temp_project_base_dir, project_name)
    expected_custom_blocks_path = os.path.join(expected_project_path, CUSTOM_BLOCKS_DIR_NAME)
    
    assert created_project_path == expected_project_path
    assert os.path.isdir(expected_project_path), "Project directory was not created."
    assert os.path.isdir(expected_custom_blocks_path), f"'{CUSTOM_BLOCKS_DIR_NAME}' subdirectory was not created."


@patch('os.path.exists')
@patch('os.makedirs')
@patch('shutil.copytree') # Mock file operations
@patch('builtins.open', new_callable=MagicMock) # Mock open for file content modification
def test_project_template_creates_custom_blocks(
    mock_open, mock_copytree, mock_makedirs, mock_path_exists,
    project_service_instance, block_service_instance, 
    temp_project_base_dir, mock_blueprint_dir
):
    """
    Test Requirement 3: when selecting a new project template to start a new project, 
    the default blocks of the template are actually created as custom blocks 
    inside the project folder, with all references and connection/metadata updated accordingly.
    Also implicitly tests part of Requirement 4 for default naming from templates.
    """
    template_name = "BasicTemplate" # Assumes a template with a few known blocks
    new_project_name = "ProjectFromBasicTemplate"

    # Mock block_service's add_block_to_project to verify it's called correctly
    # and to control its output for this test.
    # The actual add_block_to_project is tested in test_block_operations.py
    block_service_instance.add_block_to_project = MagicMock(
        side_effect=lambda project_path, blueprint_key: \
            MockBlockService().add_block_to_project(project_path, blueprint_key) # Use mock impl for return structure
    )
    
    # Patch the blueprint path lookup if your block_service needs it
    # For this test, MockBlockService's add_block_to_project has a hardcoded mock path
    # with patch.object(block_service_instance, 'get_blueprint_path', return_value=lambda key: os.path.join(mock_blueprint_dir, key)):

    # Action
    project_path, created_blocks_details = project_service_instance.create_project_from_template(
        template_name, new_project_name, temp_project_base_dir, block_service_instance
    )

    expected_project_path = os.path.join(temp_project_base_dir, new_project_name)
    assert os.path.isdir(expected_project_path)
    assert os.path.isdir(os.path.join(expected_project_path, CUSTOM_BLOCKS_DIR_NAME))

    # Assertions for Requirement 3 & 4 (default naming from template)
    # Expected blocks from "BasicTemplate"
    expected_blueprint_keys = ["INPUT_NODE", "PROCESSING_NODE", "OUTPUT_NODE"]
    
    assert block_service_instance.add_block_to_project.call_count == len(expected_blueprint_keys)

    created_block_names = [details['name'] for details in created_blocks_details]

    for bp_key in expected_blueprint_keys:
        # Check that add_block_to_project was called for each blueprint key
        # The mock for add_block_to_project in MockBlockService will generate names like "INPUT_NODE_1"
        expected_custom_name = f"{bp_key}_1" # Assuming first instance
        assert expected_custom_name in created_block_names
        
        # Find the details for this created block
        block_detail = next(b for b in created_blocks_details if b['name'] == expected_custom_name)

        custom_block_folder = os.path.join(expected_project_path, CUSTOM_BLOCKS_DIR_NAME, expected_custom_name)
        assert os.path.isdir(custom_block_folder)
        
        # Check python file name and content (simplified)
        py_file = os.path.join(custom_block_folder, expected_custom_name + PYTHON_FILE_EXT)
        assert os.path.exists(py_file)
        # In a real test, you'd read the file and use regex or AST parsing for the function name
        # For this mock, MockBlockService creates it with the right name.
        
        # Check metadata (simplified)
        app_json_path = os.path.join(custom_block_folder, METADATA_APP_JSON)
        assert os.path.exists(app_json_path)
        # In a real test, you'd parse JSON and check content.
        # MockBlockService creates a basic app.json.

    # Further checks would involve verifying connections if the template defines them,
    # and ensuring project-level metadata reflects these blocks.

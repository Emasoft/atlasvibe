# Copyright (c) 2024 Emasoft (for atlasvibe modifications and derivative work)
# Copyright (c) 2024 Flojoy (for the original "Flojoy Studio" software)
#
# This software is licensed under the MIT License.
# Refer to the LICENSE file for more details.

import os
import json
import shutil # Added import
from . import constants

class MockProjectService:
    def create_new_project(self, project_name, base_path):
        project_path = os.path.join(str(base_path), project_name)
        custom_blocks_path = os.path.join(project_path, constants.CUSTOM_BLOCKS_DIR_NAME)
        os.makedirs(custom_blocks_path, exist_ok=True)
        return project_path

    def create_project_from_template(self, template_name, new_project_name, base_path, block_service_instance):
        project_path = self.create_new_project(new_project_name, base_path)

        mock_template_blocks = []
        if template_name == "BasicTemplate":
            mock_template_blocks = [
                {"blueprint_key": constants.BLUEPRINT_INPUT_NODE, "id_in_template": "input1"},
                {"blueprint_key": constants.BLUEPRINT_PROCESSING_NODE, "id_in_template": "proc1"},
                {"blueprint_key": constants.BLUEPRINT_OUTPUT_NODE, "id_in_template": "out1"}
            ]

        created_block_details = []
        for block_def in mock_template_blocks:
            created_block_info = block_service_instance.add_block_to_project(
                project_path=project_path,
                blueprint_key=block_def["blueprint_key"],
            )
            created_block_details.append(created_block_info)
        
        return project_path, created_block_details


class MockBlockService:
    def __init__(self, blueprint_base_path):
        self.blueprint_base_path = str(blueprint_base_path)
        # In a real service, this might query a manifest or scan a directory
        # For the mock, we assume blueprints exist at the given path based on their key.
        # The available_blueprints dict can be built by scanning blueprint_base_path if needed,
        # or assumed based on test setup. For simplicity, we'll rely on folder existence.
        self.available_blueprints = self._discover_blueprints()


    def _discover_blueprints(self):
        # Simple discovery: assumes subdirectories in blueprint_base_path are blueprint keys
        discovered = {}
        if os.path.isdir(self.blueprint_base_path):
            for item in os.listdir(self.blueprint_base_path):
                item_path = os.path.join(self.blueprint_base_path, item)
                if os.path.isdir(item_path):
                    discovered[item] = {"path": item_path}
        return discovered

    def get_blueprints(self): # Added to align with usage in test_project_management
        return self.available_blueprints

    def _get_next_available_name_in_project(self, project_custom_blocks_path, base_name):
        suffix = 1
        while True:
            potential_name = f"{base_name}_{suffix}"
            if not os.path.exists(os.path.join(project_custom_blocks_path, potential_name)):
                return potential_name
            suffix += 1

    def add_block_to_project(self, project_path, blueprint_key, target_custom_block_name=None):
        if blueprint_key not in self.available_blueprints:
            # Try to re-discover if blueprints were added dynamically to the mock path
            self.available_blueprints = self._discover_blueprints()
            if blueprint_key not in self.available_blueprints:
                raise ValueError(f"Blueprint '{blueprint_key}' not found in {self.blueprint_base_path}. Available: {list(self.available_blueprints.keys())}")


        project_custom_blocks_path = os.path.join(str(project_path), constants.CUSTOM_BLOCKS_DIR_NAME)
        os.makedirs(project_custom_blocks_path, exist_ok=True)

        if target_custom_block_name:
            final_block_name = target_custom_block_name
        else:
            final_block_name = self._get_next_available_name_in_project(project_custom_blocks_path, blueprint_key)
        
        custom_block_folder_path = os.path.join(project_custom_blocks_path, final_block_name)
        os.makedirs(custom_block_folder_path, exist_ok=True)
        
        original_py_filename = blueprint_key + constants.PYTHON_FILE_EXT
        new_py_filename = final_block_name + constants.PYTHON_FILE_EXT
        new_py_filepath = os.path.join(custom_block_folder_path, new_py_filename)

        blueprint_py_path = os.path.join(self.available_blueprints[blueprint_key]['path'], original_py_filename)
        blueprint_content = f"@atlasvibe_node\ndef {blueprint_key}(param1):\n    pass" # Default content
        if os.path.exists(blueprint_py_path):
            with open(blueprint_py_path, "r") as bp_f:
                blueprint_content = bp_f.read()
        
        modified_content = blueprint_content.replace(f"def {blueprint_key}", f"def {final_block_name}")
        # A more robust replacement would use AST parsing or regex to handle various function signatures.
        # For example, replacing the first occurrence of "def blueprint_key(" or "def blueprint_key ("
        
        with open(new_py_filepath, "w") as f:
            f.write(modified_content)

        app_json_path = os.path.join(custom_block_folder_path, constants.METADATA_APP_JSON)
        original_app_json_path = os.path.join(self.available_blueprints[blueprint_key]['path'], constants.METADATA_APP_JSON)
        app_data_to_write = {"name": final_block_name, "key": final_block_name, "original_blueprint": blueprint_key}
        if os.path.exists(original_app_json_path):
            with open(original_app_json_path, "r") as oajf:
                original_app_data = json.load(oajf)
            original_app_data["name"] = final_block_name
            original_app_data["key"] = final_block_name
            original_app_data["original_blueprint"] = blueprint_key
            app_data_to_write = original_app_data
        with open(app_json_path, "w") as f:
            json.dump(app_data_to_write, f)
        
        # Simulate test file renaming (content update is more complex)
        original_test_filename = blueprint_key + constants.TEST_FILE_SUFFIX
        new_test_filename = final_block_name + constants.TEST_FILE_SUFFIX
        blueprint_test_file_path = os.path.join(self.available_blueprints[blueprint_key]['path'], original_test_filename)
        if os.path.exists(blueprint_test_file_path):
            # Just copy for now, actual renaming and content update is complex
            shutil.copy(blueprint_test_file_path, os.path.join(custom_block_folder_path, new_test_filename))


        return {
            "name": final_block_name,
            "path": custom_block_folder_path,
            "python_file": new_py_filename,
            "decorated_function_name": final_block_name
        }

    def rename_custom_block(self, project_path, old_custom_block_name, new_potential_name_base):
        project_custom_blocks_path = os.path.join(str(project_path), constants.CUSTOM_BLOCKS_DIR_NAME)
        old_block_folder_path = os.path.join(project_custom_blocks_path, old_custom_block_name)

        if not os.path.exists(old_block_folder_path):
            raise FileNotFoundError(f"Custom block '{old_custom_block_name}' not found in project.")

        # Re-discover blueprints in case they changed or for collision check
        self.available_blueprints = self._discover_blueprints()

        if new_potential_name_base in self.available_blueprints:
            final_new_name = self._get_next_available_name_in_project(project_custom_blocks_path, new_potential_name_base)
        elif os.path.exists(os.path.join(project_custom_blocks_path, new_potential_name_base)) and \
             new_potential_name_base != old_custom_block_name:
            final_new_name = self._get_next_available_name_in_project(project_custom_blocks_path, new_potential_name_base)
        else:
            if os.path.exists(os.path.join(project_custom_blocks_path, new_potential_name_base)): # Handles case where new_potential_name_base is same as old_custom_block_name but needs suffixing due to other rules
                 final_new_name = self._get_next_available_name_in_project(project_custom_blocks_path, new_potential_name_base)
            else:
                 final_new_name = new_potential_name_base

        new_block_folder_path = os.path.join(project_custom_blocks_path, final_new_name)
        
        os.rename(old_block_folder_path, new_block_folder_path)
        
        old_py_filename = old_custom_block_name + constants.PYTHON_FILE_EXT
        new_py_filename = final_new_name + constants.PYTHON_FILE_EXT
        if os.path.exists(os.path.join(new_block_folder_path, old_py_filename)):
            os.rename(os.path.join(new_block_folder_path, old_py_filename), 
                      os.path.join(new_block_folder_path, new_py_filename))
        
        py_filepath = os.path.join(new_block_folder_path, new_py_filename)
        if os.path.exists(py_filepath):
            with open(py_filepath, "r") as f:
                content = f.read()
            modified_content = content.replace(f"def {old_custom_block_name}", f"def {final_new_name}")
            with open(py_filepath, "w") as f:
                f.write(modified_content)
            
        app_json_path = os.path.join(new_block_folder_path, constants.METADATA_APP_JSON)
        if os.path.exists(app_json_path):
            with open(app_json_path, "r") as f:
                app_data = json.load(f)
            app_data["name"] = final_new_name
            app_data["key"] = final_new_name
            with open(app_json_path, "w") as f:
                json.dump(app_data, f)
        
        old_test_filename = old_custom_block_name + constants.TEST_FILE_SUFFIX
        new_test_filename = final_new_name + constants.TEST_FILE_SUFFIX
        old_test_filepath = os.path.join(new_block_folder_path, old_test_filename)
        if os.path.exists(old_test_filepath):
            os.rename(old_test_filepath, os.path.join(new_block_folder_path, new_test_filename))
            # Content update of test file is complex and not mocked here

        return {"old_name": old_custom_block_name, "new_name": final_new_name, "path": new_block_folder_path}


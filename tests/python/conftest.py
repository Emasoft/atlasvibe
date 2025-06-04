# Copyright (c) 2024 Emasoft (for atlasvibe modifications and derivative work)
# Copyright (c) 2024 Atlasvibe (for the original "Atlasvibe Studio" software)
#
# This software is licensed under the MIT License.
# Refer to the LICENSE file for more details.

import pytest
from pathlib import Path
from tests.python import constants # Absolute import for test constants

@pytest.fixture
def temp_project_base_dir(tmp_path: Path) -> Path:
    """Create a temporary base directory for projects using pytest's tmp_path."""
    base_dir = tmp_path / "projects_base"
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir

@pytest.fixture
def temp_project_dir(tmp_path: Path) -> Path:
    """Create a temporary directory for a single test project using pytest's tmp_path."""
    project_dir = tmp_path / "test_project_single" # Named to be distinct
    project_dir.mkdir(parents=True, exist_ok=True)
    # Also create the custom blocks subdirectory immediately for convenience
    (project_dir / constants.CUSTOM_BLOCKS_DIR_NAME).mkdir(parents=True, exist_ok=True)
    return project_dir

@pytest.fixture
def mock_blueprint_dir(tmp_path: Path) -> Path:
    """
    Create a temporary directory for mock blueprints (INPUT_NODE, PROCESSING_NODE, OUTPUT_NODE).
    This is primarily designed for use by test_project_management.py.
    """
    bp_dir = tmp_path / "mock_blueprints_for_project_management"
    bp_dir.mkdir(parents=True, exist_ok=True)
    
    # Create a mock INPUT_NODE blueprint
    input_node_bp = bp_dir / constants.BLUEPRINT_INPUT_NODE
    input_node_bp.mkdir()
    (input_node_bp / (constants.BLUEPRINT_INPUT_NODE + constants.PYTHON_FILE_EXT)).write_text(f"@atlasvibe_node\ndef {constants.BLUEPRINT_INPUT_NODE}(): pass")
    (input_node_bp / constants.METADATA_APP_JSON).write_text(f'{{"name": "{constants.BLUEPRINT_INPUT_NODE}", "key": "{constants.BLUEPRINT_INPUT_NODE}"}}')

    # Create a mock PROCESSING_NODE blueprint
    proc_node_bp = bp_dir / constants.BLUEPRINT_PROCESSING_NODE
    proc_node_bp.mkdir()
    (proc_node_bp / (constants.BLUEPRINT_PROCESSING_NODE + constants.PYTHON_FILE_EXT)).write_text(f"@atlasvibe_node\ndef {constants.BLUEPRINT_PROCESSING_NODE}(input): pass")
    (proc_node_bp / constants.METADATA_APP_JSON).write_text(f'{{"name": "{constants.BLUEPRINT_PROCESSING_NODE}", "key": "{constants.BLUEPRINT_PROCESSING_NODE}"}}')

    # Create a mock OUTPUT_NODE blueprint
    output_node_bp = bp_dir / constants.BLUEPRINT_OUTPUT_NODE
    output_node_bp.mkdir()
    (output_node_bp / (constants.BLUEPRINT_OUTPUT_NODE + constants.PYTHON_FILE_EXT)).write_text(f"@atlasvibe_node\ndef {constants.BLUEPRINT_OUTPUT_NODE}(input): pass")
    (output_node_bp / constants.METADATA_APP_JSON).write_text(f'{{"name": "{constants.BLUEPRINT_OUTPUT_NODE}", "key": "{constants.BLUEPRINT_OUTPUT_NODE}"}}')
    
    return bp_dir

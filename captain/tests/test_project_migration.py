#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Initial test implementation for project migration functionality
# - Tests for old format detection, migration process, and edge cases
# - Tests for hardware block handling and error scenarios
#

"""Test suite for project migration functionality."""

import json
from captain.utils.project_migration import (
    is_old_format_project,
    find_blueprint_block,
    migrate_project_to_new_format,
    needs_migration,
)


class TestOldFormatDetection:
    """Tests for detecting old format projects."""

    def test_detects_old_format_with_blueprint_paths(self):
        """Test that projects with blueprint paths are detected as old format."""
        project_data = {
            "rfInstance": {
                "nodes": [
                    {
                        "data": {
                            "func": "SINE",
                            "path": "GENERATORS/WAVEFORMS/SINE/SINE.py",
                            "isCustom": False,
                        }
                    }
                ]
            }
        }
        assert is_old_format_project(project_data) is True

    def test_detects_new_format_with_custom_blocks(self):
        """Test that projects with custom blocks are detected as new format."""
        project_data = {
            "rfInstance": {
                "nodes": [
                    {
                        "data": {
                            "func": "SINE_1",
                            "path": "atlasvibe_blocks/SINE_1/SINE_1.py",
                            "isCustom": True,
                        }
                    }
                ]
            }
        }
        assert is_old_format_project(project_data) is False

    def test_handles_empty_project(self):
        """Test handling of empty project data."""
        project_data = {"rfInstance": {"nodes": []}}
        assert is_old_format_project(project_data) is False

    def test_handles_missing_rfinstance(self):
        """Test handling of project without rfInstance."""
        project_data = {}
        assert is_old_format_project(project_data) is False


class TestBlueprintFinding:
    """Tests for finding blueprint blocks."""

    def test_finds_existing_blueprint(self):
        """Test finding a blueprint block that exists."""
        # This test assumes CONSTANT block exists in the blocks directory
        path = find_blueprint_block("CONSTANT")
        assert path is not None
        assert path.name == "CONSTANT"
        assert (path / "CONSTANT.py").exists()

    def test_returns_none_for_nonexistent_blueprint(self):
        """Test that None is returned for non-existent blueprints."""
        path = find_blueprint_block("NONEXISTENT_BLOCK_XYZ")
        assert path is None


class TestProjectMigration:
    """Tests for the project migration process."""

    def test_migrate_simple_project(self, tmp_path):
        """Test migrating a simple project with one block."""
        # Create a test project
        project_file = tmp_path / "test.atlasvibe"
        project_data = {
            "name": "Test Project",
            "rfInstance": {
                "nodes": [
                    {
                        "id": "node1",
                        "data": {
                            "func": "CONSTANT",
                            "path": "GENERATORS/CONSTANTS/CONSTANT/CONSTANT.py",
                            "label": "CONSTANT",
                            "isCustom": False,
                        },
                    }
                ],
                "edges": [],
            },
        }

        # Write project file
        with open(project_file, "w") as f:
            json.dump(project_data, f)

        # Migrate the project
        migrated_data, created_blocks = migrate_project_to_new_format(str(project_file), project_data, dry_run=False)

        # Verify migration results
        assert len(created_blocks) == 1
        assert created_blocks[0] == "CONSTANT_1"

        # Check migrated data
        node = migrated_data["rfInstance"]["nodes"][0]
        assert node["data"]["func"] == "CONSTANT_1"
        assert node["data"]["isCustom"] is True
        assert node["data"]["path"] == "atlasvibe_blocks/CONSTANT_1/CONSTANT_1.py"
        assert node["data"]["label"] == "CONSTANT_1"

        # Verify custom block was created
        blocks_dir = tmp_path / "atlasvibe_blocks" / "CONSTANT_1"
        assert blocks_dir.exists()
        assert (blocks_dir / "CONSTANT_1.py").exists()

    def test_migrate_project_with_hardware_blocks(self, tmp_path):
        """Test migrating a project with hardware blocks that have no blueprints."""
        project_file = tmp_path / "hardware_test.atlasvibe"
        project_data = {
            "name": "Hardware Test",
            "rfInstance": {
                "nodes": [
                    {
                        "id": "node1",
                        "data": {
                            "func": "SPECIAL_HARDWARE_BLOCK",
                            "path": "HARDWARE/SPECIAL/SPECIAL_HARDWARE_BLOCK.py",
                            "label": "SPECIAL_HARDWARE_BLOCK",
                            "isCustom": False,
                        },
                    }
                ],
                "edges": [],
            },
        }

        # Write project file
        with open(project_file, "w") as f:
            json.dump(project_data, f)

        # Migrate the project
        migrated_data, created_blocks = migrate_project_to_new_format(str(project_file), project_data, dry_run=False)

        # Verify no blocks were created for hardware blocks
        assert len(created_blocks) == 0

        # Check that hardware block was marked appropriately
        node = migrated_data["rfInstance"]["nodes"][0]
        assert node["data"].get("isHardwareBlock") is True
        assert node["data"].get("requiresHardware") is True

    def test_migrate_already_migrated_project(self, tmp_path):
        """Test that already migrated projects are not migrated again."""
        project_file = tmp_path / "already_migrated.atlasvibe"
        project_data = {
            "name": "Already Migrated",
            "rfInstance": {
                "nodes": [
                    {
                        "id": "node1",
                        "data": {
                            "func": "SINE_1",
                            "path": "atlasvibe_blocks/SINE_1/SINE_1.py",
                            "label": "SINE_1",
                            "isCustom": True,
                        },
                    }
                ],
                "edges": [],
            },
        }

        # Write project file
        with open(project_file, "w") as f:
            json.dump(project_data, f)

        # Attempt migration
        migrated_data, created_blocks = migrate_project_to_new_format(str(project_file), project_data, dry_run=False)

        # Verify no changes were made
        assert len(created_blocks) == 0
        assert migrated_data == project_data

    def test_dry_run_migration(self, tmp_path):
        """Test dry run mode doesn't create files."""
        project_file = tmp_path / "dry_run_test.atlasvibe"
        project_data = {
            "name": "Dry Run Test",
            "rfInstance": {
                "nodes": [
                    {
                        "id": "node1",
                        "data": {
                            "func": "CONSTANT",
                            "path": "GENERATORS/CONSTANTS/CONSTANT/CONSTANT.py",
                            "label": "CONSTANT",
                            "isCustom": False,
                        },
                    }
                ],
                "edges": [],
            },
        }

        # Migrate in dry run mode
        migrated_data, created_blocks = migrate_project_to_new_format(str(project_file), project_data, dry_run=True)

        # Verify migration would happen
        assert len(created_blocks) == 1

        # Verify no files were created
        blocks_dir = tmp_path / "atlasvibe_blocks"
        assert not blocks_dir.exists()

    def test_unique_block_naming(self, tmp_path):
        """Test that unique names are generated for duplicate blocks."""
        project_file = tmp_path / "duplicate_test.atlasvibe"
        project_data = {
            "name": "Duplicate Test",
            "rfInstance": {
                "nodes": [
                    {
                        "id": "node1",
                        "data": {
                            "func": "CONSTANT",
                            "path": "GENERATORS/CONSTANTS/CONSTANT/CONSTANT.py",
                            "label": "CONSTANT",
                            "isCustom": False,
                        },
                    },
                    {
                        "id": "node2",
                        "data": {
                            "func": "CONSTANT",
                            "path": "GENERATORS/CONSTANTS/CONSTANT/CONSTANT.py",
                            "label": "CONSTANT",
                            "isCustom": False,
                        },
                    },
                ],
                "edges": [],
            },
        }

        # Write project file
        with open(project_file, "w") as f:
            json.dump(project_data, f)

        # Migrate the project
        migrated_data, created_blocks = migrate_project_to_new_format(str(project_file), project_data, dry_run=False)

        # Verify both blocks get the same custom name (reused)
        assert len(created_blocks) == 1
        assert created_blocks[0] == "CONSTANT_1"

        # Both nodes should reference the same custom block
        nodes = migrated_data["rfInstance"]["nodes"]
        assert nodes[0]["data"]["func"] == "CONSTANT_1"
        assert nodes[1]["data"]["func"] == "CONSTANT_1"


class TestNeedsMigration:
    """Tests for checking if migration is needed."""

    def test_needs_migration_for_old_format(self, tmp_path):
        """Test that old format projects need migration."""
        project_file = tmp_path / "old_format.atlasvibe"
        project_data = {
            "rfInstance": {
                "nodes": [
                    {
                        "data": {
                            "func": "SINE",
                            "path": "GENERATORS/WAVEFORMS/SINE/SINE.py",
                            "isCustom": False,
                        }
                    }
                ]
            }
        }

        with open(project_file, "w") as f:
            json.dump(project_data, f)

        assert needs_migration(str(project_file)) is True

    def test_no_migration_needed_for_new_format(self, tmp_path):
        """Test that new format projects don't need migration."""
        project_file = tmp_path / "new_format.atlasvibe"
        project_data = {
            "rfInstance": {
                "nodes": [
                    {
                        "data": {
                            "func": "SINE_1",
                            "path": "atlasvibe_blocks/SINE_1/SINE_1.py",
                            "isCustom": True,
                        }
                    }
                ]
            }
        }

        with open(project_file, "w") as f:
            json.dump(project_data, f)

        assert needs_migration(str(project_file)) is False

    def test_handles_invalid_json(self, tmp_path):
        """Test handling of invalid JSON files."""
        project_file = tmp_path / "invalid.atlasvibe"
        project_file.write_text("{ invalid json }")

        assert needs_migration(str(project_file)) is False

    def test_handles_nonexistent_file(self):
        """Test handling of non-existent files."""
        assert needs_migration("/nonexistent/file.atlasvibe") is False

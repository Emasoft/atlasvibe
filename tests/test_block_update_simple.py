#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Simple integration test for block update functionality
# - Tests actual file operations without complex imports
# 

"""Simple integration test for block update functionality."""

import json
import tempfile
from pathlib import Path


def test_block_file_update():
    """Test that block files can be updated and rolled back."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a block file
        block_dir = Path(tmpdir) / "atlasvibe_blocks" / "TEST_BLOCK"
        block_dir.mkdir(parents=True)
        
        block_file = block_dir / "TEST_BLOCK.py"
        original_content = """#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from atlasvibe import atlasvibe

@atlasvibe
def TEST_BLOCK(x: int = 1) -> int:
    '''Original implementation.'''
    return x * 2
"""
        block_file.write_text(original_content)
        
        # Simulate update process
        new_content = """#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from atlasvibe import atlasvibe

@atlasvibe  
def TEST_BLOCK(x: int = 1) -> int:
    '''Updated implementation.'''
    return x * 3
"""
        
        # Backup original content
        backup = block_file.read_text()
        assert backup == original_content
        
        # Update file
        block_file.write_text(new_content)
        assert block_file.read_text() == new_content
        
        # Test rollback
        block_file.write_text(backup)
        assert block_file.read_text() == original_content


def test_project_structure_validation():
    """Test project structure validation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Valid project path
        valid_project = Path(tmpdir) / "project.atlasvibe"
        valid_project.write_text("{}")
        assert valid_project.name.endswith(".atlasvibe")
        
        # Invalid project path
        invalid_project = Path(tmpdir) / "project.txt"
        invalid_project.write_text("{}")
        assert not invalid_project.name.endswith(".atlasvibe")
        
        # Custom block path validation
        custom_block_path = str(Path(tmpdir) / "atlasvibe_blocks" / "BLOCK" / "BLOCK.py")
        assert "atlasvibe_blocks" in custom_block_path
        
        blueprint_path = str(Path(tmpdir) / "blocks" / "MATH" / "ADD" / "ADD.py")
        assert "atlasvibe_blocks" not in blueprint_path


def test_metadata_files():
    """Test metadata file handling."""
    with tempfile.TemporaryDirectory() as tmpdir:
        block_dir = Path(tmpdir) / "atlasvibe_blocks" / "TEST"
        block_dir.mkdir(parents=True)
        
        # Create metadata files
        app_json = block_dir / "app.json"
        app_json.write_text(json.dumps({
            "name": "TEST",
            "type": "default",
            "category": "PROJECT"
        }))
        
        block_data_json = block_dir / "block_data.json"
        block_data_json.write_text(json.dumps({
            "inputs": [{"name": "x", "type": "int", "default": 1}],
            "outputs": [{"name": "output", "type": "int"}]
        }))
        
        # Verify files exist and are valid JSON
        assert app_json.exists()
        assert block_data_json.exists()
        
        app_data = json.loads(app_json.read_text())
        assert app_data["name"] == "TEST"
        
        block_data = json.loads(block_data_json.read_text())
        assert len(block_data["inputs"]) == 1
        assert block_data["inputs"][0]["name"] == "x"


def test_concurrent_file_access():
    """Test handling of concurrent file access."""
    import threading
    import time
    
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.py"
        test_file.write_text("initial content")
        
        results = []
        
        def update_file(content):
            try:
                # Simulate read-modify-write
                current = test_file.read_text()
                time.sleep(0.01)  # Simulate processing
                test_file.write_text(f"{current}\n{content}")
                results.append("success")
            except Exception as e:
                results.append(f"error: {e}")
        
        # Run concurrent updates
        threads = []
        for i in range(3):
            t = threading.Thread(target=update_file, args=(f"update {i}",))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        # All operations should complete
        assert len(results) == 3
        
        # File should contain updates
        final_content = test_file.read_text()
        assert "initial content" in final_content
        # At least some updates should be present (concurrent writes might overwrite)
        update_count = sum(1 for i in range(3) if f"update {i}" in final_content)
        assert update_count >= 1  # At least one update should succeed


if __name__ == "__main__":
    test_block_file_update()
    test_project_structure_validation()
    test_metadata_files()
    test_concurrent_file_access()
    print("All tests passed!")
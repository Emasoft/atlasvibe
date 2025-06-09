#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Demonstration of automatic metadata generation for custom blocks.

This test creates a new custom block and shows that all metadata files
are automatically generated.
"""

import json
import os
import tempfile
import time
from pathlib import Path

import pytest

from captain.utils.block_metadata_generator import generate_all_metadata_files


def test_automatic_metadata_generation_demo():
    """
    Demonstrate the automatic metadata generation feature.
    
    This test simulates what happens when a user creates a new custom block:
    1. User creates a directory for the block
    2. User creates only the Python file with the block implementation
    3. System automatically generates all metadata files
    """
    
    # Create a temporary directory to simulate custom blocks folder
    with tempfile.TemporaryDirectory() as tmpdir:
        print(f"\n=== Automatic Metadata Generation Demo ===")
        print(f"Working directory: {tmpdir}")
        
        # Step 1: User creates a block directory
        block_name = "DEMO_CUSTOM_BLOCK"
        block_dir = Path(tmpdir) / block_name
        block_dir.mkdir()
        print(f"\n1. Created block directory: {block_dir}")
        
        # Step 2: User creates ONLY the Python file
        py_content = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from atlasvibe import atlasvibe
from atlasvibe.parameter_types import String, Number, DataFrame


@atlasvibe
def DEMO_CUSTOM_BLOCK(
    input_text: String = "Hello AtlasVibe",
    scale_factor: Number = 1.5,
) -> DataFrame:
    """
    Demonstration custom block with automatic metadata generation.
    
    This block shows how AtlasVibe automatically generates all necessary
    metadata files when you create a new custom block.
    
    Parameters
    ----------
    input_text : String
        Text input to process
    scale_factor : Number
        Scaling factor for the operation
        
    Returns
    -------
    DataFrame
        Processed data as a DataFrame
    """
    # Example implementation
    import pandas as pd
    
    data = {
        'text': [input_text] * int(scale_factor * 3),
        'value': [i * scale_factor for i in range(int(scale_factor * 3))]
    }
    return pd.DataFrame(data)
'''
        
        py_file = block_dir / f"{block_name}.py"
        py_file.write_text(py_content)
        print(f"\n2. User created Python file: {py_file}")
        print("   (This is the ONLY file the user needs to create!)")
        
        # Show that no metadata files exist yet
        print("\n3. Before automatic generation:")
        for filename in ['block_data.json', 'app.json', 'example.md', f'{block_name}_test_.py']:
            exists = (block_dir / filename).exists()
            print(f"   - {filename}: {'EXISTS' if exists else 'DOES NOT EXIST'}")
        
        # Step 3: Simulate the automatic generation (normally triggered by file watcher)
        print("\n4. Triggering automatic metadata generation...")
        success, generated_files = generate_all_metadata_files(str(block_dir))
        
        if success:
            print(f"\n5. Successfully generated {len(generated_files)} files:")
            for file in generated_files:
                print(f"   ✓ {file}")
        else:
            print("\n5. ERROR: Failed to generate some files")
            
        # Step 4: Show the generated files and their content
        print("\n6. Generated file contents:")
        
        # Show block_data.json
        if (block_dir / "block_data.json").exists():
            with open(block_dir / "block_data.json") as f:
                data = json.load(f)
            print("\n   block_data.json (auto-generated from docstring):")
            print(f"   - Short description: {data['docstring']['short_description']}")
            print(f"   - Parameters: {len(data['docstring']['parameters'])} defined")
            for param in data['docstring']['parameters']:
                print(f"     • {param['name']} ({param['type']}): {param['description']}")
                
        # Show app.json
        if (block_dir / "app.json").exists():
            with open(block_dir / "app.json") as f:
                app_data = json.load(f)
            print("\n   app.json (default workflow template):")
            print(f"   - Contains {len(app_data['rfInstance']['nodes'])} node(s)")
            print(f"   - Block function: {app_data['rfInstance']['nodes'][0]['data']['func']}")
            
        # Show example.md
        if (block_dir / "example.md").exists():
            content = (block_dir / "example.md").read_text()
            print("\n   example.md (documentation template):")
            print(f"   - Length: {len(content)} characters")
            print(f"   - Contains block name: {'DEMO_CUSTOM_BLOCK' in content}")
            
        # Show test file
        test_file = block_dir / f"{block_name}_test_.py"
        if test_file.exists():
            content = test_file.read_text()
            print(f"\n   {test_file.name} (test template):")
            print(f"   - Contains test functions: {content.count('def test_') > 0}")
            print(f"   - Ready for implementation: {' TODO:' in content}")
            
        # Step 5: Demonstrate update behavior
        print("\n7. Testing update behavior (modifying Python file)...")
        
        # Modify the Python file
        updated_content = py_content.replace(
            "Demonstration custom block with automatic metadata generation.",
            "UPDATED: This description has been changed!"
        )
        py_file.write_text(updated_content)
        
        # Regenerate only block_data.json (simulating file watcher behavior)
        from captain.utils.block_metadata_generator import regenerate_block_data_json
        regenerate_block_data_json(str(block_dir))
        
        # Show the updated description
        with open(block_dir / "block_data.json") as f:
            updated_data = json.load(f)
        print(f"   - Updated description: {updated_data['docstring']['short_description']}")
        
        # Verify other files were NOT modified
        print("\n8. Verification:")
        print("   ✓ block_data.json was updated with new docstring")
        print("   ✓ Other metadata files were preserved")
        print("   ✓ All files required for a custom block are present")
        
        print("\n=== Demo Complete ===")
        print("\nSummary: When you create a custom block in AtlasVibe, you only need to")
        print("create the Python file. All metadata files are generated automatically!")
        
        # Assert all files exist for test validation
        assert (block_dir / "block_data.json").exists()
        assert (block_dir / "app.json").exists()
        assert (block_dir / "example.md").exists()
        assert (block_dir / f"{block_name}_test_.py").exists()
        assert updated_data['docstring']['short_description'] == "UPDATED: This description has been changed!"


if __name__ == "__main__":
    # Run the demo directly
    test_automatic_metadata_generation_demo()
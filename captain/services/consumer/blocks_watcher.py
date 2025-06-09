#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Added extraction of specific block paths from file changes
# - Updated manifest_update broadcast to include blockPaths array
# - Improved path extraction to identify block-specific changes
# - Added automatic metadata generation for new custom blocks
# - Regenerates block_data.json when Python files are modified
# 

# Copyright (c) 2024 Emasoft (for atlasvibe modifications and derivative work)
# Copyright (c) 2024 Atlasvibe (for the original "Atlasvibe Studio" software)
#
# This software is licensed under the MIT License.
# Refer to the LICENSE file for more details.

from captain.internal.wsmanager import ConnectionManager
from captain.utils.blocks_path import get_blocks_path
from captain.utils.logger import logger
from captain.utils.block_metadata_generator import (
    generate_all_metadata_files,
    regenerate_block_data_json
)
from watchfiles import awatch
from pathlib import Path
import threading
import os


class BlocksWatcher:
    def __init__(self) -> None:
        self.ws = ConnectionManager.get_instance()

    async def run(self, stop_flag: threading.Event):
        paths_to_watch: list[str] = []
        blocks_path = get_blocks_path()
        paths_to_watch.append(blocks_path)
        custom_path_file = Path.home() / ".atlasvibe" / "custom_blocks_path.txt" # CHANGED .atlasvibe to .atlasvibe
        if Path.exists(custom_path_file):
            with open(custom_path_file) as f:
                paths_to_watch.append(f.read())
        logger.info(f"Starting file watcher for blocks dirs {paths_to_watch}")

        async for changes in awatch(*paths_to_watch, stop_event=stop_flag):
            logger.info(f"Detected {len(changes)} file changes in {paths_to_watch}..")
            
            # Extract block paths from the changed files
            block_paths = set()
            for change_type, file_path in changes:
                # Convert to Path object for easier manipulation
                path = Path(file_path)
                
                # Check if this is a Python file in a block directory
                if path.suffix == '.py' and path.stem == path.parent.name:
                    # This is likely a block's main Python file
                    block_dir = str(path.parent)
                    
                    # Check if this is a new block (no metadata files exist)
                    has_metadata = any(
                        (path.parent / f).exists() 
                        for f in ['block_data.json', 'app.json', 'example.md']
                    )
                    
                    if not has_metadata:
                        # This is a new block, generate all metadata files
                        logger.info(f"New block detected: {path.stem}, generating metadata files...")
                        success, generated_files = generate_all_metadata_files(block_dir)
                        if success:
                            logger.info(f"Generated metadata files for {path.stem}: {', '.join(generated_files)}")
                        else:
                            logger.error(f"Failed to generate some metadata files for {path.stem}")
                    else:
                        # Existing block modified, regenerate block_data.json
                        logger.info(f"Block {path.stem} modified, regenerating block_data.json...")
                        if regenerate_block_data_json(block_dir):
                            logger.info(f"Regenerated block_data.json for {path.stem}")
                        else:
                            logger.error(f"Failed to regenerate block_data.json for {path.stem}")
                    
                    # Extract the relative path from the blocks directory
                    for watch_path in paths_to_watch:
                        try:
                            relative_path = path.relative_to(watch_path)
                            # Convert to the block path format used in the manifest
                            block_path = str(relative_path.parent).replace(os.sep, '/')
                            block_paths.add(block_path)
                            logger.info(f"Block {block_path} has been modified")
                            break
                        except ValueError:
                            # File is not relative to this watch path
                            continue
                elif path.name in ['block_data.json', 'app.json', 'example.md']:
                    # Metadata file changed, get the block directory
                    for watch_path in paths_to_watch:
                        try:
                            relative_path = path.relative_to(watch_path)
                            block_path = str(relative_path.parent).replace(os.sep, '/')
                            block_paths.add(block_path)
                            logger.info(f"Block {block_path} metadata has been modified")
                            break
                        except ValueError:
                            continue

            if self.ws.active_connections_map:
                await self.ws.broadcast({
                    "type": "manifest_update",
                    "blockPaths": list(block_paths) if block_paths else None
                })

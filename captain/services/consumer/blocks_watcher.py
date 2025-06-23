#!/usr/bin/env python3
# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Added extraction of specific block paths from file changes
# - Updated manifest_update broadcast to include blockPaths array
# - Improved path extraction to identify block-specific changes
# - Added automatic metadata generation for new custom blocks
# - Regenerates block_data.json when Python files are modified
#


from captain.internal.wsmanager import ConnectionManager
from captain.utils.blocks_path import get_blocks_path
from captain.utils.logger import logger
from captain.utils.block_metadata_generator import (
    generate_all_metadata_files,
    regenerate_block_data_json,
)
from captain.types.worker import RegenerationMessage
from watchfiles import awatch
from pathlib import Path
import threading
import os
import time


class BlocksWatcher:
    def __init__(self) -> None:
        self.ws = ConnectionManager.get_instance()

    async def _handle_block_change(self, block_file_path: str):
        """Handle a block file change and broadcast regeneration events."""
        path = Path(block_file_path)
        block_name = path.stem
        block_dir = str(path.parent)

        # Broadcast regeneration start event
        start_msg = RegenerationMessage(
            type="regeneration_start",
            block_name=block_name,
            block_path=block_dir,
            status="regenerating",
            success=None,
            error=None,
        )
        await self.ws.broadcast(start_msg)

        try:
            # Regenerate block_data.json
            success = regenerate_block_data_json(block_dir)

            if success:
                # Broadcast regeneration complete event
                complete_msg = RegenerationMessage(
                    type="regeneration_complete",
                    block_name=block_name,
                    block_path=block_dir,
                    status="completed",
                    success=True,
                    error=None,
                )
                await self.ws.broadcast(complete_msg)
                logger.info(f"Successfully regenerated metadata for {block_name}")
            else:
                # Broadcast regeneration error event
                error_msg = RegenerationMessage(
                    type="regeneration_error",
                    block_name=block_name,
                    block_path=block_dir,
                    status="error",
                    success=False,
                    error="Failed to regenerate block_data.json",
                )
                await self.ws.broadcast(error_msg)
                logger.error(f"Failed to regenerate metadata for {block_name}")

        except Exception as e:
            # Broadcast regeneration error event
            error_msg = RegenerationMessage(
                type="regeneration_error",
                block_name=block_name,
                block_path=block_dir,
                status="error",
                success=False,
                error=str(e),
            )
            await self.ws.broadcast(error_msg)
            logger.error(f"Error regenerating metadata for {block_name}: {e}")

    async def run(self, stop_flag: threading.Event):
        paths_to_watch: list[str] = []
        blocks_path = get_blocks_path()

        # Track when we start watching to ignore initial directory creation
        self._watch_start_time = time.time()

        # Only add paths that actually exist
        if Path(blocks_path).exists():
            paths_to_watch.append(blocks_path)

        custom_path_file = Path.home() / ".atlasvibe" / "custom_blocks_path.txt"  # CHANGED .atlasvibe to .atlasvibe
        if Path.exists(custom_path_file):
            with open(custom_path_file) as f:
                custom_path = f.read().strip()
                if custom_path and Path(custom_path).exists():
                    paths_to_watch.append(custom_path)

        if not paths_to_watch:
            logger.warning("No valid paths to watch for blocks")
            return

        logger.info(f"Starting file watcher for blocks dirs {paths_to_watch}")

        async for changes in awatch(*paths_to_watch, stop_event=stop_flag):
            # Filter out changes that are just directory creation without content
            meaningful_changes = []
            for change_type, file_path in changes:
                path = Path(file_path)

                # Skip if it's just the atlasvibe_blocks directory being created
                if path.name == "atlasvibe_blocks" and path.is_dir():
                    # Check if directory is empty or only has __init__.py
                    contents = list(path.iterdir())
                    if len(contents) == 0 or (len(contents) == 1 and contents[0].name == "__init__.py"):
                        logger.debug(f"Ignoring empty directory creation: {path}")
                        continue

                meaningful_changes.append((change_type, file_path))

            if not meaningful_changes:
                continue

            logger.info(f"Detected {len(meaningful_changes)} meaningful file changes in {paths_to_watch}..")

            # Extract block paths from the changed files
            block_paths = set()
            changes = meaningful_changes  # Use filtered changes
            for change_type, file_path in changes:
                # Convert to Path object for easier manipulation
                path = Path(file_path)

                # Check if this is a Python file in a block directory
                if path.suffix == ".py" and path.stem == path.parent.name:
                    # This is likely a block's main Python file
                    block_dir = str(path.parent)

                    # Check if this is a new block (no metadata files exist)
                    has_metadata = any((path.parent / f).exists() for f in ["block_data.json", "app.json", "example.md"])

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
                            block_path = str(relative_path.parent).replace(os.sep, "/")
                            block_paths.add(block_path)
                            logger.info(f"Block {block_path} has been modified")
                            break
                        except ValueError:
                            # File is not relative to this watch path
                            continue
                elif path.name in ["block_data.json", "app.json", "example.md"]:
                    # Metadata file changed, get the block directory
                    for watch_path in paths_to_watch:
                        try:
                            relative_path = path.relative_to(watch_path)
                            block_path = str(relative_path.parent).replace(os.sep, "/")
                            block_paths.add(block_path)
                            logger.info(f"Block {block_path} metadata has been modified")
                            break
                        except ValueError:
                            continue

            if self.ws.active_connections_map:
                await self.ws.broadcast(
                    {
                        "type": "manifest_update",
                        "blockPaths": list(block_paths) if block_paths else None,
                    }
                )

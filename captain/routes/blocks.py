import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Response, HTTPException
from pydantic import BaseModel

from captain.internal.manager import WatchManager
from captain.utils.manifest.generate_manifest import generate_manifest
from captain.utils.blocks_metadata import generate_metadata
from captain.utils.import_blocks import create_map
from captain.utils.logger import logger
from captain.utils.project_structure import (
    copy_blueprint_to_project,
    ProjectStructureError,
    validate_block_name
)
from captain.utils.blocks_path import get_blocks_path
from captain.utils.manifest.build_manifest import process_block_directory

router = APIRouter(tags=["blocks"])


class CreateCustomBlockRequest(BaseModel):
    """Request model for creating a custom block."""
    blueprint_key: str
    new_block_name: str
    project_path: str


@router.get("/blocks/manifest/")
async def get_manifest(blocks_path: str | None = None, project_path: str | None = None):
    # Pre-generate the blocks map to synchronize it with the manifest
    create_map(custom_blocks_dir=blocks_path, project_path=project_path)
    try:
        manifest = generate_manifest(blocks_path=blocks_path, project_path=project_path)
        return manifest
    except Exception as e:
        logger.error(
            f"error in get_manifest(): {e} traceback: {e.with_traceback(e.__traceback__)}"
        )
        return Response(
            status_code=400,
            content=json.dumps({"success": False, "error": "\n".join(e.args)}),
        )


@router.get("/blocks/metadata/")
async def get_metadata(
    blocks_path: str | None = None, custom_dir_changed: bool = False
):
    try:
        metadata_map = generate_metadata(custom_blocks_dir=blocks_path)
        if custom_dir_changed:
            watch_manager = WatchManager.get_instance()
            watch_manager.restart()
        return metadata_map
    except Exception as e:
        logger.error(
            f"error in get_metadata(): {e}, traceback: {e.with_traceback(e.__traceback__)}"
        )
        return Response(
            status_code=400,
            content=json.dumps({"success": False, "error": "\n".join(e.args)}),
        )


def find_blueprint_path(blueprint_key: str) -> Optional[Path]:
    """Find the path to a blueprint block by its key.
    
    Args:
        blueprint_key: The key/name of the blueprint block
        
    Returns:
        Path to the blueprint directory if found, None otherwise
    """
    blocks_base_path = Path(get_blocks_path())
    
    # Use glob to search more efficiently
    for pattern in ["*/*", "*/*/*"]:  # Support 2 and 3 level nesting
        for block_dir in blocks_base_path.glob(f"{pattern}/{blueprint_key}"):
            if block_dir.is_dir():
                return block_dir
    
    return None


@router.post("/blocks/create-custom/")
async def create_custom_block(request: CreateCustomBlockRequest):
    """Create a custom block from a blueprint for a specific project.
    
    Args:
        request: Request containing blueprint key, new block name, and project path
        
    Returns:
        Block definition with additional path information
    """
    # Validate the block name early
    try:
        validate_block_name(request.new_block_name)
    except ProjectStructureError as e:
        raise HTTPException(status_code=422, detail=str(e))
    
    # Validate project path
    if not request.project_path or not request.project_path.endswith('.atlasvibe'):
        raise HTTPException(
            status_code=422,
            detail="Invalid project path. Must be a .atlasvibe file"
        )
    
    try:
        # Find the blueprint block directory
        blueprint_path = find_blueprint_path(request.blueprint_key)
        
        if not blueprint_path:
            raise HTTPException(
                status_code=404,
                detail=f"Blueprint block '{request.blueprint_key}' not found"
            )
        
        # Copy the blueprint to the project
        new_block_path = copy_blueprint_to_project(
            str(blueprint_path),
            request.project_path,
            request.new_block_name
        )
        
        # Generate manifest for the new block
        block_manifest = process_block_directory(
            Path(new_block_path),
            request.new_block_name
        )
        
        if not block_manifest:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate manifest for new custom block"
            )
        
        # Add the path to the manifest
        block_manifest["path"] = new_block_path
        
        logger.info(f"Created custom block '{request.new_block_name}' at {new_block_path}")
        
        return block_manifest
        
    except ProjectStructureError as e:
        logger.error(f"Project structure error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        logger.error(f"Error creating custom block: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Initial implementation of project route handlers
# - Added migrate_project endpoint for converting old format projects
# - Added check_migration endpoint to check if migration is needed
# - Integrated with project migration utilities
#

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import json
from pathlib import Path
import shutil

from captain.utils.project_migration import (
    migrate_project_to_new_format,
    needs_migration,
    is_old_format_project,
    ProjectMigrationError,
)
from captain.utils.logger import logger
from captain.utils.fastapi_error_handler import fastapi_error_handler


router = APIRouter(tags=["project"])


class MigrateProjectRequest(BaseModel):
    """Request model for migrating a project."""

    project_path: str
    dry_run: bool = False


class CheckMigrationRequest(BaseModel):
    """Request model for checking if project needs migration."""

    project_path: str
    project_data: Optional[dict] = None


class MigrationResponse(BaseModel):
    """Response model for migration operations."""

    needs_migration: bool
    migrated: bool = False
    created_blocks: List[str] = []
    project_data: Optional[dict] = None
    message: str = ""


@router.post("/project/check-migration/")
@fastapi_error_handler(
    operation="checking project migration status",
    error_code_prefix="CHECK_MIGRATION",
)
async def check_project_migration(request: CheckMigrationRequest) -> MigrationResponse:
    """Check if a project needs migration from old to new format.

    Args:
        request: Request containing project path or project data

    Returns:
        Migration status response
    """
    if request.project_data:
        # Check from provided data
        needs_migration_flag = is_old_format_project(request.project_data)
    else:
        # Check from file
        needs_migration_flag = needs_migration(request.project_path)

    return MigrationResponse(
        needs_migration=needs_migration_flag,
        message=(
            "Project is in old blueprint format and needs migration"
            if needs_migration_flag
            else "Project is already in new custom block format"
        ),
    )


@router.post("/project/migrate/")
@fastapi_error_handler(
    operation="migrating project to new format",
    error_code_prefix="MIGRATE_PROJECT",
    log_request=True,
    log_duration=True,
)
async def migrate_project(request: MigrateProjectRequest) -> MigrationResponse:
    """Migrate a project from old blueprint format to new custom block format.

    Args:
        request: Request containing project path and options

    Returns:
        Migration response with new project data

    Raises:
        HTTPException: If migration fails
    """
    # Validate project path
    project_file = Path(request.project_path)
    if not project_file.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Project file not found: {request.project_path}",
        )

    if project_file.suffix != ".atlasvibe":
        raise HTTPException(
            status_code=422,
            detail="Invalid project file. Must be a .atlasvibe file",
        )

    # Load project data
    try:
        with open(project_file, "r") as f:
            project_data = json.load(f)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid project file format: {e}",
        )

    # Check if migration is needed
    if not is_old_format_project(project_data):
        return MigrationResponse(
            needs_migration=False,
            migrated=False,
            message="Project is already in new format, no migration needed",
            project_data=project_data,
        )

    # Perform migration
    try:
        migrated_data, created_blocks = migrate_project_to_new_format(
            request.project_path,
            project_data,
            dry_run=request.dry_run,
        )

        # Save migrated project if not in dry run mode
        if not request.dry_run:
            # Backup original project
            backup_path = project_file.with_suffix(".atlasvibe.backup")
            shutil.copy2(project_file, backup_path)
            logger.info(f"Created backup at {backup_path}")

            # Save migrated project
            with open(project_file, "w") as f:
                json.dump(migrated_data, f, indent=2)
            logger.info(f"Saved migrated project to {project_file}")

        return MigrationResponse(
            needs_migration=False,
            migrated=True,
            created_blocks=created_blocks,
            project_data=migrated_data,
            message=(
                f"Successfully migrated project. Created {len(created_blocks)} custom blocks."
                if not request.dry_run
                else f"Dry run complete. Would create {len(created_blocks)} custom blocks."
            ),
        )

    except ProjectMigrationError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Migration failed: {e}",
        )
    except Exception as e:
        logger.error(f"Unexpected error during migration: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error during migration: {str(e)}",
        )


#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Refactored to use standardized error handling utilities
# - Added FastAPI error handler decorator to all endpoints
# - Replaced json.dumps() with FastAPI's automatic JSON serialization
# - Added retry logic for git operations
# - Improved error messages and sanitization
# - Added specific error codes for different failure scenarios
#

import subprocess
from typing import Annotated
from fastapi import APIRouter, Header
import os

from captain.utils.blocks_path import get_atlasvibe_dir
from captain.utils.logger import logger
from captain.utils.fastapi_error_handler import (
    fastapi_error_handler,
)
from captain.utils.shared.error_utils import error_context


router = APIRouter(tags=["test_profile"])


class GitError(Exception):
    """Custom exception for git-related errors."""

    pass


class ProfileError(Exception):
    """Custom exception for profile-related errors."""

    pass


@router.get("/test_profile/install/")
@fastapi_error_handler(
    operation="installing test profile",
    error_code_prefix="TEST_PROFILE",
    log_request=True,
    retry=True,
    max_attempts=3,
    retry_exceptions=(ConnectionError, OSError),
)
async def install(url: Annotated[str, Header()]):
    """
    Download a git repo to the local machine if it doesn't exist + verify its state
    - Currently done for Github. (infer that the repo doesn't contain space)
    - Private repo is not (directly) supported
    """
    logger.info(f"Installing the profile from the url: {url}")

    with error_context("verifying git installation", logger):
        verify_git_install()

    with error_context("getting profiles directory", logger):
        profiles_path = get_profiles_dir()
        profile_path = get_profile_path_from_url(profiles_path, url)

    # Find the profile
    if not os.path.exists(profile_path):
        # Clone the repo if it doesn't exist
        with error_context(f"cloning repository from {url}", logger):
            cmd = ["git", "clone", "--depth", "1", url, profile_path]
            res = subprocess.run(cmd, capture_output=True)
            if res.returncode != 0:
                stdout = res.stdout.decode("utf-8").strip()
                stderr = res.stderr.decode("utf-8").strip()
                logger.error(f"Error while cloning url: {stdout} - {stderr}")

                # Check for common error patterns
                if "unable to connect" in stderr.lower() or "could not resolve" in stderr.lower():
                    raise ConnectionError("Unable to connect to repository")
                elif "repository not found" in stderr.lower() or "not found" in stderr.lower():
                    raise GitError("Repository not found or access denied")
                else:
                    raise GitError(f"Failed to clone repository (code: {res.returncode})")
    else:
        with error_context("updating to origin main", logger):
            update_to_origin_main(profile_path)

    with error_context("getting commit hash", logger):
        commit_hash = get_commit_hash(profile_path)

    # Always use / in the path for compatibility
    profile_path = profile_path.replace(os.sep, "/")

    return {"profile_root": profile_path, "hash": commit_hash}


@router.post("/test_profile/checkout/{commit_hash}/")
@fastapi_error_handler(
    operation="checking out commit",
    error_code_prefix="TEST_PROFILE",
    log_request=True,
    retry=True,
    max_attempts=2,
    retry_exceptions=(ConnectionError,),
)
async def checkout(url: Annotated[str, Header()], commit_hash: str):
    """Checkout a specific commit for a test profile."""
    logger.info(f"Switching to the commit: {commit_hash} for the profile: {url}")

    with error_context("verifying git installation", logger):
        verify_git_install()

    with error_context("getting profile path", logger):
        profiles_path = get_profiles_dir()
        profile_path = get_profile_path_from_url(profiles_path, url)
        curr_commit_hash = get_commit_hash(profile_path)

    if curr_commit_hash != commit_hash:
        # Fetch the latest changes
        with error_context("fetching latest changes", logger):
            cmd = ["git", "-C", profile_path, "fetch", "--all"]
            res = subprocess.run(cmd, capture_output=True)
            if res.returncode != 0:
                stderr = res.stderr.decode("utf-8").strip()
                if "unable to access" in stderr.lower() or "could not resolve" in stderr.lower():
                    raise ConnectionError("Unable to connect to repository")
                raise GitError(f"Failed to fetch repository (code: {res.returncode})")

        # Switch to the specific commit
        with error_context(f"checking out commit {commit_hash}", logger):
            cmd = ["git", "-C", profile_path, "checkout", commit_hash]
            res = subprocess.run(cmd, capture_output=True)
            if res.returncode != 0:
                stderr = res.stderr.decode("utf-8").strip()
                if "pathspec" in stderr.lower() and "did not match" in stderr.lower():
                    raise GitError(f"Commit {commit_hash} not found")
                raise GitError(f"Failed to checkout commit (code: {res.returncode})")

    commit_hash = get_commit_hash(profile_path)

    return {"profile_root": profile_path, "hash": commit_hash}


# Helper functions ------------------------------------------------------------


def get_profile_path_from_url(profiles_path: str, url: str) -> str:
    """Get the profile directory name from the url"""
    profile_name = url.split("/")[-1]
    if profile_name.endswith(".git"):
        profile_name = profile_name[:-4]
    logger.info(f"Profile name: {profile_name}")
    profile_root = os.path.join(profiles_path, profile_name)
    return profile_root


def verify_git_install():
    """Verify if git is installed on the system"""
    cmd = ["git", "--version"]
    res = subprocess.run(cmd, capture_output=True)
    if res.returncode != 0:
        raise RuntimeError("Git is not found on your system")


def get_profiles_dir() -> str:
    """Get or create the test profiles directory."""
    profiles_dir = os.path.join(get_atlasvibe_dir(), f"test_profiles{os.sep}")
    if not os.path.exists(profiles_dir):
        os.makedirs(profiles_dir)
    return profiles_dir


def get_commit_hash(profile_path: str) -> str:
    """Get the commit hash of the current env."""
    cmd = ["git", "-C", profile_path, "rev-parse", "HEAD"]
    res = subprocess.run(cmd, capture_output=True)
    if res.returncode != 0:
        raise GitError(f"Failed to get commit hash (code: {res.returncode})")
    return res.stdout.strip().decode()


def update_to_origin_main(profile_path: str):
    """Update the local repo to the latest version"""
    logger.info("Updating the repo to the origin main")

    # Verify the repo is clean (no changes so the user doesn't lose any work)
    cmd = ["git", "-C", profile_path, "status", "--porcelain"]
    res = subprocess.run(cmd, capture_output=True)
    if res.returncode != 0:
        raise GitError(f"Failed to check repository status (code: {res.returncode})")
    if res.stdout.strip() != b"":
        raise ProfileError("Repository has uncommitted changes")

    # Get the latest changes
    cmd = ["git", "-C", profile_path, "fetch", "--all"]
    res = subprocess.run(cmd, capture_output=True)
    if res.returncode != 0:
        stderr = res.stderr.decode("utf-8").strip()
        if "unable to access" in stderr.lower() or "could not resolve" in stderr.lower():
            raise ConnectionError("Unable to connect to repository")
        raise GitError(f"Failed to fetch repository (code: {res.returncode})")

    # Switch to the latest change
    cmd = ["git", "-C", profile_path, "checkout", "origin/main"]
    res = subprocess.run(cmd, capture_output=True)
    if res.returncode != 0:
        raise GitError(f"Failed to checkout origin/main (code: {res.returncode})")

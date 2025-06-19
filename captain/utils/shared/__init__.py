#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Shared utility modules to reduce code duplication across the AtlasVibe codebase.
"""

from .json_utils import (
    load_json_file,
    save_json_file,
    update_json_file,
    merge_json_files,
)

from .path_utils import (
    get_block_python_file,
    get_block_metadata_file,
    get_block_app_file,
    get_block_example_file,
    get_block_test_file,
    get_block_venv_dir,
    find_project_root,
    ensure_directory_exists,
    safe_path_join,
    get_relative_path,
    find_files_by_pattern,
    is_valid_block_directory,
)

from .error_utils import (
    safe_execute,
    with_error_handling,
    with_retry,
    error_context,
    ErrorAccumulator,
    format_exception_chain,
    create_error_handler,
)

__all__ = [
    # JSON utilities
    "load_json_file",
    "save_json_file",
    "update_json_file",
    "merge_json_files",
    # Path utilities
    "get_block_python_file",
    "get_block_metadata_file",
    "get_block_app_file",
    "get_block_example_file",
    "get_block_test_file",
    "get_block_venv_dir",
    "find_project_root",
    "ensure_directory_exists",
    "safe_path_join",
    "get_relative_path",
    "find_files_by_pattern",
    "is_valid_block_directory",
    # Error utilities
    "safe_execute",
    "with_error_handling",
    "with_retry",
    "error_context",
    "ErrorAccumulator",
    "format_exception_chain",
    "create_error_handler",
]

import os
from typing import Any, Optional, Union

from captain.utils.blocks_path import get_blocks_path
from captain.utils.manifest.build_manifest import create_manifest
from captain.utils.project_structure import get_project_blocks_dir, validate_project_structure
from captain.utils.logger import logger

__all__ = ["generate_manifest"]

NAME_MAP = {
    "AI_ML": "AI & ML",
    "DATA": "Data",
    "DSP": "Digital Signal Processing",
    "IMAGE": "Image",
    "HARDWARE": "Hardware",
    "CONTROL_FLOW": "Control Flow",
    "MATH": "Math",
    "DEBUGGING": "Debugging",
    "ETL": "ETL",
    "NUMPY": "numpy",
    "LINALG": "np.linalg",
    "RANDOM": "np.rand",
    "SCIPY": "scipy",
    "SIGNAL": "sp.signal",
    "STATS": "sp.stats",
    "GAMES": "Games",
    "COMPUTER_VISION": "Computer Vision",
    "default": "Default Blocks",
    "TYPE_CASTING": "Type Casting",
}

# Types that are allowed in the manifest, this is for styling in the frontend.
# A node will inherit the type of its parent if it is not in the allowed types.
ALLOWED_TYPES = [
    "AI_ML",
    "DATA",
    "VISUALIZATION",
    "MATH",
    "ETL",
    "DSP",
    "IMAGE",
    "CONTROL_FLOW",
    "CONDITIONALS",
    "HARDWARE",
    "NUMPY",
    "SCIPY",
    "GAMES",
    "DEBUGGING",
    "COMPUTER_VISION",
    "TRANSFORM",
    "EXTRACT",
    "LOAD",
    "TYPE_CASTING",
    "FUNCTION_GENERATORS",
    "ROBOTICS",
    "MOTORS",
    "PROTOCOLS",
    "NATIONAL_INSTRUMENTS",
    "DAQ_BOARDS",
    "IMAGING",
    "MULTIMETERS",
    "OSCILLOSCOPES",
]

# Sort order in sidebar
ORDERING = [
    "AI_ML",
    "DATA",
    "MATH",
    "ETL",
    "DSP",
    "IMAGE",
    "CONTROL_FLOW",
    "COMPUTER_VISION",
    "HARDWARE",
    "NUMPY",
    "SCIPY",
    "DEBUGGING",
]


def browse_directories(dir_path: str, cur_type: Optional[str] = None, depth: int = 0):
    result: dict[str, Union[str, list[Any], None]] = {}
    basename = os.path.basename(dir_path)
    result["name"] = "ROOT" if depth == 0 else NAME_MAP.get(basename, basename)
    if result["name"] != "ROOT":
        result["key"] = basename

    result["children"] = []
    entries = sorted(
        os.scandir(dir_path), key=lambda e: e.name
    )  # Sort entries alphabetically

    for entry in entries:
        if entry.is_dir():
            if (
                entry.name.startswith(".")
                or entry.name.startswith("_")
                or entry.name == "assets"
                or entry.name == "utils"
                or entry.name == "MANIFEST"
                or "examples" in entry.path
                or "a1-[autogen]" in entry.path
                or "appendix" in entry.path
                or not os.listdir(entry)
            ):
                continue

            cur_type = (
                basename
                if basename in ALLOWED_TYPES  # give current type precedence
                else (
                    cur_type
                    if cur_type in ALLOWED_TYPES  # otherwise inherit if allowed
                    else "default"
                )  # else use default
            )

            subdir = browse_directories(entry.path, cur_type, depth=depth + 1)
            result["children"].append(subdir)
        elif entry.is_file() and entry.name.endswith(".py"):
            continue
    if not result["children"] and os.listdir(dir_path):
        try:
            n_file_name = f"{os.path.basename(dir_path)}.py"
            n_path = os.path.join(dir_path, n_file_name)
            result = create_manifest(n_path)
        except Exception as e:
            raise ValueError(
                f"Failed to generate manifest from {os.path.basename(dir_path)}.py, reason: {str(e)}"
            )

        if not result.get("type"):
            result["type"] = cur_type
        result["children"] = None

    return result


def sort_order(element: dict[str, Any]):
    try:
        return ORDERING.index(element["key"])
    except ValueError:
        return len(ORDERING)


def generate_manifest(blocks_path: str | None, project_path: str | None = None):
    """Generate manifest including both blueprint and project blocks.
    
    Args:
        blocks_path: Optional custom blocks path (legacy parameter)
        project_path: Optional path to .atlasvibe project file
        
    Returns:
        Manifest dictionary with all available blocks
    """
    blocks_path = blocks_path if blocks_path else get_blocks_path()
    blocks_map = browse_directories(blocks_path)
    blocks_map["children"].sort(key=sort_order)  # type: ignore
    
    # Add project-specific blocks if project path is provided
    if project_path and validate_project_structure(project_path):
        project_blocks_dir = get_project_blocks_dir(project_path)
        
        # Create a project blocks section
        project_blocks = {
            "name": "Project Blocks",
            "key": "PROJECT_BLOCKS",
            "type": "PROJECT",
            "children": []
        }
        
        # Add each project block
        for block_dir in sorted(project_blocks_dir.iterdir()):
            if block_dir.is_dir() and not block_dir.name.startswith('_'):
                py_file = block_dir / f"{block_dir.name}.py"
                if py_file.exists():
                    try:
                        block_manifest = create_manifest(str(py_file))
                        if block_manifest:
                            block_manifest["type"] = "PROJECT"
                            block_manifest["isCustom"] = True
                            project_blocks["children"].append(block_manifest)
                    except Exception as e:
                        logger.error(f"Failed to create manifest for project block {block_dir.name}: {e}")
        
        # Add project blocks at the beginning if there are any
        if project_blocks["children"]:
            blocks_map["children"].insert(0, project_blocks)
    
    return blocks_map

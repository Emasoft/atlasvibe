from typing import Any, cast

from atlasvibe import NoInitFunctionError, get_node_init_function

from captain.models.topology import Topology
from captain.utils.project_blocks_loader import get_module_for_block, get_project_loader


def pre_import_functions(topology: Topology, project_path: str | None = None):
    functions: dict[str, str] = {}
    errors: dict[str, str] = {}
    for block_id in cast(list[str], topology.original_graph.nodes):
        # get the block function
        block = cast(dict[str, Any], topology.original_graph.nodes[block_id])
        cmd: str = block["cmd"]
        module = get_module_func(cmd, project_path)
        if module is None:
            errors[block_id] = f"Failed to load module for block '{cmd}'"
            continue
        func = getattr(module, cmd)

        preflight = next(
            (
                f
                for f in module.__dict__.values()
                if callable(f) and getattr(f, "is_atlasvibe_preflight", False)
            ),
            None,
        )

        if preflight is not None:
            try:
                preflight()
            except Exception as e:
                errors[block_id] = str(e)

        # check if the func has an init function, and initialize it if it does to the specified node id
        try:
            init_func = get_node_init_function(func)
            init_func.run(
                block_id, block["init_ctrls"]
            )  # node id is used to specify storage: each node of the same type will have its own storage
        except NoInitFunctionError:
            pass
        except Exception as e:
            errors[block_id] = str(e)

        functions[block_id] = func
    return functions, errors


mapping: dict[str, str] = {}


def get_module_func(file_name: str, project_path: str | None = None):
    """Get module for a block function, supporting project-specific blocks.
    
    Args:
        file_name: Name of the block/function
        project_path: Optional path to .atlasvibe project file
        
    Returns:
        Module object or None if not found
    """
    # Use the new project-aware loader
    return get_module_for_block(file_name, project_path)


def create_map(custom_blocks_dir: str | None, project_path: str | None = None):
    """Create mapping of blocks.
    
    This function is kept for backward compatibility but now delegates
    to the new project-aware loader.
    
    Args:
        custom_blocks_dir: Custom blocks directory (legacy parameter)
        project_path: Optional path to .atlasvibe project file
    """
    loader = get_project_loader(project_path)
    loader.initialize()
    
    # Update the global mapping for backward compatibility
    global mapping
    mapping.clear()
    mapping.update(loader.combined_mapping)
    
    if custom_blocks_dir:
        mapping["root"] = custom_blocks_dir

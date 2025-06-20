from typing import Optional
from pkgs.atlasvibe.atlasvibe.atlasvibe_python import atlasvibe
from pkgs.atlasvibe.atlasvibe.data_container import Scalar, OrderedPair
from pkgs.atlasvibe.atlasvibe.small_memory import SmallMemory
from pkgs.atlasvibe.atlasvibe.parameter_types import NodeReference

memory_key = "LOOP_INDEX"


@atlasvibe
def LOOP_INDEX_1(
    loop_node: NodeReference,
    default: Optional[OrderedPair | Scalar] = None,
) -> Scalar:
    """Load the loop index from the LOOP node.

    A loop index in Atlasvibe starts at 1 and increases by 1 for each loop.

    Parameters
    ----------
    loop_node : str
        The LOOP node to track the loop index from.

    Returns
    -------
    Scalar
        The loop index in Scalar form.
    """

    ref_loop_node = loop_node.unwrap()

    if ref_loop_node == "" or "LOOP" not in ref_loop_node:
        raise ValueError("A LOOP node id must be given.")

    loop_info = SmallMemory().read_memory(ref_loop_node, "loop-info")
    if loop_info is None:
        c = 1
    else:
        c = loop_info.get("current_iteration")

    return Scalar(c=float(c))

from typing import Literal, Optional

from pkgs.atlasvibe.atlasvibe import DataContainer, atlasvibe_node  # CHANGED


@atlasvibe_node(node_type="TEST_TYPE")  # CHANGED
def SELECTS(
    default: DataContainer,
    option1: Literal["a", "b", "c"] = "a",
    option2: Optional[Literal["d", "e", "f"]] = None,
    option3: Literal[1, 2, 3] = 3,
) -> DataContainer:
    return default

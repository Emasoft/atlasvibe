# Copyright (c) 2024 Emasoft (for atlasvibe modifications and derivative work)
# Copyright (c) 2024 Atlasvibe (for the original "Atlasvibe Studio" software)
#
# This software is licensed under the MIT License.
# Refer to the LICENSE file for more details.

from typing import Literal, Optional

from atlasvibe import DataContainer, atlasvibe_node # CHANGED


@atlasvibe_node(node_type="TEST_TYPE") # CHANGED
def SELECTS(
    default: DataContainer,
    option1: Literal["a", "b", "c"] = "a",
    option2: Optional[Literal["d", "e", "f"]] = None,
    option3: Literal[1, 2, 3] = 3,
) -> DataContainer:
    return default

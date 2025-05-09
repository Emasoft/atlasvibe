# Copyright (c) 2024 Emasoft (for atlasvibe modifications and derivative work)
# Copyright (c) 2024 Flojoy (for the original "Flojoy Studio" software)
#
# This software is licensed under the MIT License.
# Refer to the LICENSE file for more details.

from flojoy import DataContainer, atlasvibe_node # CHANGED


@atlasvibe_node(node_type="default") # CHANGED
def DEFAULT_NODE(default: DataContainer) -> DataContainer:
    return DataContainer(x=[2], y=[2])

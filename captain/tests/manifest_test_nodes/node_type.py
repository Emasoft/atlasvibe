# Copyright (c) 2024 Emasoft (for atlasvibe modifications and derivative work)
# Copyright (c) 2024 Atlasvibe (for the original "Atlasvibe Studio" software)
#
# This software is licensed under the MIT License.
# Refer to the LICENSE file for more details.

from pkgs.atlasvibe.atlasvibe import DataContainer, atlasvibe_node # CHANGED


@atlasvibe_node(node_type="default") # CHANGED
def DEFAULT_NODE(default: DataContainer) -> DataContainer:
    return DataContainer(x=[2], y=[2])

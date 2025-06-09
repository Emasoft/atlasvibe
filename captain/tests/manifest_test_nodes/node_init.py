# Copyright (c) 2024 Emasoft (for atlasvibe modifications and derivative work)
# Copyright (c) 2024 Atlasvibe (for the original "Atlasvibe Studio" software)
#
# This software is licensed under the MIT License.
# Refer to the LICENSE file for more details.

import numpy as np
from pkgs.atlasvibe.atlasvibe import Array, NodeInitContainer, OrderedPair, atlasvibe_node, node_initialization # CHANGED


@atlasvibe_node(node_type="TEST_TYPE") # CHANGED
def NODE_INIT(init_container: NodeInitContainer, a: int = 0) -> OrderedPair:
    return OrderedPair(x=np.array([]), y=np.array([]))


@node_initialization(for_node=NODE_INIT)
def init(foo: str, bar: int, baz: float, quux: bool, asdf: Array, s: str = "hello"):
    return "test"

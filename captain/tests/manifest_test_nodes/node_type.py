from pkgs.atlasvibe.atlasvibe import DataContainer, atlasvibe_node  # CHANGED


@atlasvibe_node(node_type="default")  # CHANGED
def DEFAULT_NODE(default: DataContainer) -> DataContainer:
    return DataContainer(x=[2], y=[2])

from pkgs.atlasvibe.atlasvibe import (
    DataContainer,
    JobResultBuilder,
    atlasvibe_node,
)  # CHANGED


@atlasvibe_node  # CHANGED
def END(default: DataContainer):
    return JobResultBuilder().from_inputs([default]).flow_to_nodes([]).build()

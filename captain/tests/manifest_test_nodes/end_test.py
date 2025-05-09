# Copyright (c) 2024 Emasoft (for atlasvibe modifications and derivative work)
# Copyright (c) 2024 Flojoy (for the original "Flojoy Studio" software)
#
# This software is licensed under the MIT License.
# Refer to the LICENSE file for more details.

from flojoy import DataContainer, JobResultBuilder, atlasvibe_node # CHANGED


@atlasvibe_node # CHANGED
def END(default: DataContainer):
    return JobResultBuilder().from_inputs([default]).flow_to_nodes([]).build()

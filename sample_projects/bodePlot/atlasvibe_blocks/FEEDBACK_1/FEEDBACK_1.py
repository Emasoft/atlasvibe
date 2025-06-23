# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

from typing import Any, Optional
from pkgs.atlasvibe.atlasvibe.parameter_types import NodeReference
from pkgs.atlasvibe.atlasvibe.job_result_builder import JobResultBuilder
from pkgs.atlasvibe.atlasvibe.atlasvibe_python import atlasvibe
from pkgs.atlasvibe.atlasvibe.data_container import DataContainer
from pkgs.atlasvibe.atlasvibe.job_service import JobService


@atlasvibe
def FEEDBACK_1(
    referred_node: NodeReference,
    default: Optional[DataContainer] = None,
) -> Any:
    """Capture and save the results of a specified block over time. This block is almost always used in a LOOP.

    If the result is not found, it passes the result of the parent node.

    Parameters
    ----------
    referred_node : str
        The node ID to capture the result from.

    Returns
    -------
    DataContainer
        The result of the specified node ID, or the result of the parent node if it was not found.
    """

    result = JobService().get_job_result(referred_node.ref)
    if result:
        return result
    else:
        return JobResultBuilder().from_inputs([default] if default else []).flow_to_directions(["default"]).build()

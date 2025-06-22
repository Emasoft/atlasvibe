# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

from pkgs.atlasvibe.atlasvibe.atlasvibe_python import atlasvibe
from pkgs.atlasvibe.atlasvibe.data_container import DataContainer
from pkgs.atlasvibe.atlasvibe.job_result_builder import JobResultBuilder
import time
from typing import Optional, cast


@atlasvibe
def TIMER(
    default: Optional[DataContainer] = None,
    sleep_time: float = 0,
) -> DataContainer:
    """Sleep (pause program execution) for a specified number of seconds.

    Parameters
    ----------
    sleep_time : float
        number of seconds to sleep

    Returns
    -------
    Optional[DataContainer]
        Returns the input if one was passed in.
    """

    time.sleep(sleep_time)
    result = cast(
        DataContainer,
        JobResultBuilder().from_inputs([default] if default else []).build(),
    )

    return result

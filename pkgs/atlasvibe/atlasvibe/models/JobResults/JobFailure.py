# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

from .JobFeedback import JobFeedback

__all__ = ["JobFailure"]


class JobFailure(JobFeedback):
    def __init__(self, func_name, node_id, error, jobset_id):
        super().__init__(jobset_id)
        self.func_name = func_name
        self.node_id = node_id
        self.error = error

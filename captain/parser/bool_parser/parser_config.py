# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

from captain.parser.bool_parser.expressions.models import (
    And,
    GetPassFail,
    Not,
    Or,
    Expression,
)


class Rule:
    def __init__(self, order_of_operations):
        self.order_of_operations: list[set[Expression]] = order_of_operations


rules = Rule(
    order_of_operations=[
        {GetPassFail},
        {Not},
        {And},
        {Or},
    ]
)

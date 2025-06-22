# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

from typing import Union
from captain.parser.bool_parser.expressions.models import (
    Identifier,
    LeftParenthesis,
    Operator,
    RightParenthesis,
    Literal,
)

Token = Union[Operator, LeftParenthesis, RightParenthesis, Identifier, Literal]

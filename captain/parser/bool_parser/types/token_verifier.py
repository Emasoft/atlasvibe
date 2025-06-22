# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

from typing import Callable, List
from captain.parser.bool_parser.expressions.models import SymbolTableType

from captain.parser.bool_parser.types.expressions import Token

TokenVerifier = Callable[
    ...,  # i dont think python supports optional params typing hint (or like a parameter type must be in some set)
    None,
]


class VerificationContainer:
    def __init__(
        self,
        tokens: List[Token],
        symbol_table: SymbolTableType,
        all_identifiers: set[str],
    ):
        self.tokens = tokens
        self.symbol_table = symbol_table
        self.all_identifiers = all_identifiers

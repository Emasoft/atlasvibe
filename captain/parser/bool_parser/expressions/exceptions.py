# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.


class InvalidCharacter(Exception):
    def __init__(self, message=""):
        self.message = "Invalid character: " + message
        super().__init__(self.message)


class MissingRightParenthesis(Exception):
    def __init__(self, message=""):
        self.message = "Missing right parenthesis: " + message
        super().__init__(self.message)


class MissingLeftParenthesis(Exception):
    def __init__(self, message=""):
        self.message = "Missing left parenthesis" + message
        super().__init__(self.message)


class InvalidExpression(Exception):
    def __init__(self, message=""):
        self.message = "The boolean expression is invalid: " + message
        super().__init__(self.message)


class TargetNumberMismatch(Exception):
    def __init__(self, message=""):
        self.message = "Mismatch in number of expected targets: " + message
        super().__init__(self.message)


class TestNotRan(Exception):
    def __init__(self, message=""):
        self.message = "The test hasn't been ran:" + message
        super().__init__(self.message)


class MatchError(Exception):
    def __init__(self, message=""):
        self.message = "Something went wrong during matching: " + message
        super().__init__(self.message)


class InvalidIdentifier(Exception):
    def __init__(self, message=""):
        self.message = "Invalid identifier: " + message
        super().__init__(self.message)


class EarlyIdentifier(Exception):
    def __init__(self, message=""):
        self.message = (
            f"Unable to access test result for {message} as it's executed afterward"
        )

#!/usr/bin/env python3
# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Initial implementation of Python code validator for AtlasVibe blocks
# - AST-based syntax validation with detailed error messages
# - Import resolution and validation
# - Type annotation checking
# - Variable usage analysis
# - AtlasVibe-specific validation rules
#

"""
Python code validator for AtlasVibe blocks.

This module provides comprehensive Python code validation including:
- Syntax checking using AST
- Import validation
- Type annotation checking
- Variable usage analysis
- AtlasVibe-specific rules (decorator usage, docstring format)
"""

import ast
import builtins
import importlib.util
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import docstring_parser
from docstring_parser import ParseError


@dataclass
class ValidationError:
    """Represents a validation error in the code.

    Args:
        line: Line number where the error occurs (1-indexed).
        column: Column number where the error occurs (0-indexed).
        message: Human-readable error message.
        severity: Error severity ('error', 'warning', 'info').
        category: Error category for filtering/grouping.
        suggestion: Optional suggestion for fixing the error.
    """

    line: int
    column: int
    message: str
    severity: str = "error"
    category: str = "syntax"
    suggestion: Optional[str] = None


@dataclass
class CompletionItem:
    """Represents a code completion suggestion.

    Args:
        label: The text to insert.
        kind: Type of completion ('function', 'class', 'variable', etc.).
        detail: Additional information about the item.
        documentation: Full documentation/docstring.
        insert_text: Text to actually insert (if different from label).
    """

    label: str
    kind: str
    detail: Optional[str] = None
    documentation: Optional[str] = None
    insert_text: Optional[str] = None


class PythonValidator:
    """Validates Python code for AtlasVibe blocks."""

    def __init__(self, project_path: Optional[Path] = None):
        """Initialize the validator.

        Args:
            project_path: Path to the project directory for import resolution.
        """
        self.project_path = project_path
        self.builtin_names = set(dir(builtins))
        self.atlasvibe_imports = {
            "atlasvibe",
            "atlasvibe_sdk",
            "DataContainer",
            "Scalar",
            "Vector",
            "Matrix",
            "DataFrame",
            "OrderedPair",
            "Surface",
        }

    def validate_code(
        self, code: str, filename: str = "<unknown>"
    ) -> List[ValidationError]:
        """Validate Python code and return list of errors.

        Args:
            code: Python code to validate.
            filename: Name of the file being validated.

        Returns:
            List of validation errors found in the code.
        """
        errors = []

        # First, try to parse the code
        try:
            tree = ast.parse(code, filename=filename)
        except SyntaxError as e:
            errors.append(
                ValidationError(
                    line=e.lineno or 1,
                    column=e.offset or 0,
                    message=f"Syntax error: {e.msg}",
                    severity="error",
                    category="syntax",
                    suggestion=self._get_syntax_error_suggestion(e.msg),
                )
            )
            return errors

        # Run various validators
        errors.extend(self._validate_imports(tree, code))
        errors.extend(self._validate_atlasvibe_decorator(tree, code))
        errors.extend(self._validate_docstring(tree, code))
        errors.extend(self._validate_variables(tree))
        errors.extend(self._validate_type_annotations(tree))
        errors.extend(self._validate_complexity(tree))
        errors.extend(self._validate_missing_return_types(tree))

        return errors

    def _validate_imports(self, tree: ast.AST, code: str) -> List[ValidationError]:
        """Validate import statements."""
        errors = []
        visitor = ImportVisitor()
        visitor.visit(tree)

        for import_info in visitor.imports:
            module_name = import_info["module"]
            line = import_info["line"]
            col = import_info["col"]

            # Check if module can be imported
            if not self._can_import(module_name):
                errors.append(
                    ValidationError(
                        line=line,
                        column=col,
                        message=f"Cannot import module '{module_name}'",
                        severity="error",
                        category="import",
                        suggestion="Install the package or check the module name",
                    )
                )

        return errors

    def _validate_atlasvibe_decorator(
        self, tree: ast.AST, code: str
    ) -> List[ValidationError]:
        """Validate AtlasVibe decorator usage."""
        errors = []
        visitor = DecoratorVisitor()
        visitor.visit(tree)

        # Check if there's an @atlasvibe decorated function
        atlasvibe_funcs = [
            f
            for f in visitor.decorated_functions
            if any(d in ["atlasvibe", "atlasvibe_node"] for d in f["decorators"])
        ]

        if not atlasvibe_funcs:
            errors.append(
                ValidationError(
                    line=1,
                    column=0,
                    message="No @atlasvibe decorated function found",
                    severity="warning",
                    category="atlasvibe",
                    suggestion="Add @atlasvibe decorator to your main block function",
                )
            )
        elif len(atlasvibe_funcs) > 1:
            for func in atlasvibe_funcs[1:]:
                errors.append(
                    ValidationError(
                        line=func["line"],
                        column=0,
                        message="Multiple @atlasvibe decorated functions found",
                        severity="error",
                        category="atlasvibe",
                        suggestion="Only one function should have @atlasvibe decorator",
                    )
                )

        return errors

    def _validate_docstring(self, tree: ast.AST, code: str) -> List[ValidationError]:
        """Validate docstring format for AtlasVibe blocks."""
        errors = []
        visitor = FunctionVisitor()
        visitor.visit(tree)

        for func in visitor.functions:
            # Only validate AtlasVibe decorated functions
            if not any(self._is_atlasvibe_decorator(d) for d in func.decorator_list):
                continue

            docstring = ast.get_docstring(func)
            if not docstring:
                errors.append(
                    ValidationError(
                        line=func.lineno,
                        column=func.col_offset,
                        message=f"Function '{func.name}' missing docstring",
                        severity="error",
                        category="docstring",
                        suggestion="Add a NumPy-style docstring describing the function",
                    )
                )
                continue

            # Parse and validate docstring format
            try:
                parsed = docstring_parser.parse(docstring)

                # Check for short description
                if not parsed.short_description:
                    errors.append(
                        ValidationError(
                            line=func.lineno + 1,
                            column=0,
                            message="Docstring missing short description",
                            severity="warning",
                            category="docstring",
                            suggestion="Add a brief one-line description at the start",
                        )
                    )

                # Get function parameters
                func_params = {
                    arg.arg for arg in func.args.args if arg.arg not in ["self", "cls"]
                }

                # Check documented parameters
                doc_params = {p.arg_name for p in parsed.params}

                # Find missing parameters
                missing = func_params - doc_params
                for param in missing:
                    errors.append(
                        ValidationError(
                            line=func.lineno,
                            column=0,
                            message=f"Parameter '{param}' not documented in docstring",
                            severity="error",
                            category="docstring",
                            suggestion=f"Add '{param} : type\\n    Description' to Parameters section",
                        )
                    )

                # Find extra parameters
                extra = doc_params - func_params
                for param in extra:
                    errors.append(
                        ValidationError(
                            line=func.lineno,
                            column=0,
                            message=f"Documented parameter '{param}' not in function signature",
                            severity="warning",
                            category="docstring",
                        )
                    )

                # Check parameter format
                for param in parsed.params:
                    if not param.type_name:
                        errors.append(
                            ValidationError(
                                line=func.lineno,
                                column=0,
                                message=f"Parameter '{param.arg_name}' missing type annotation",
                                severity="warning",
                                category="docstring",
                                suggestion=f"Add type after parameter name: '{param.arg_name} : type'",
                            )
                        )

                # Check for Returns section
                if not parsed.returns and func.returns:
                    errors.append(
                        ValidationError(
                            line=func.lineno,
                            column=0,
                            message="Function has return type but docstring missing Returns section",
                            severity="warning",
                            category="docstring",
                            suggestion="Add 'Returns\\n-------\\ntype\\n    Description' section",
                        )
                    )

            except ParseError as e:
                errors.append(
                    ValidationError(
                        line=func.lineno + 1,
                        column=0,
                        message=f"Invalid docstring format: {str(e)}",
                        severity="error",
                        category="docstring",
                        suggestion="Use NumPy-style docstring format",
                    )
                )

        return errors

    def _validate_variables(self, tree: ast.AST) -> List[ValidationError]:
        """Validate variable usage (undefined variables, etc.)."""
        errors = []
        visitor = VariableVisitor()
        visitor.visit(tree)

        # Find undefined variables
        undefined = (
            visitor.used_names
            - visitor.defined_names
            - self.builtin_names
            - self.atlasvibe_imports
        )

        for var_info in visitor.variable_uses:
            if var_info["name"] in undefined:
                errors.append(
                    ValidationError(
                        line=var_info["line"],
                        column=var_info["col"],
                        message=f"Undefined variable '{var_info['name']}'",
                        severity="error",
                        category="variable",
                        suggestion=f"Define '{var_info['name']}' before using it",
                    )
                )

        return errors

    def _validate_type_annotations(self, tree: ast.AST) -> List[ValidationError]:
        """Validate type annotations."""
        errors = []
        visitor = TypeAnnotationVisitor()
        visitor.visit(tree)

        for ann_info in visitor.annotations:
            # Basic validation - check if type names are valid
            type_str = ann_info["annotation"]
            if self._is_invalid_type(type_str):
                errors.append(
                    ValidationError(
                        line=ann_info["line"],
                        column=ann_info["col"],
                        message=f"Invalid type annotation: {type_str}",
                        severity="warning",
                        category="type",
                        suggestion="Use valid Python types or import custom types",
                    )
                )

        return errors

    def _can_import(self, module_name: str) -> bool:
        """Check if a module can be imported."""
        # Special handling for atlasvibe modules
        if module_name.startswith("atlasvibe") or module_name.startswith(
            "pkgs.atlasvibe"
        ):
            return True

        # Try to find the module
        try:
            spec = importlib.util.find_spec(module_name)
            return spec is not None
        except (ImportError, ValueError, ModuleNotFoundError):
            return False

    def _is_atlasvibe_decorator(self, decorator: ast.AST) -> bool:
        """Check if a decorator is an AtlasVibe decorator."""
        if isinstance(decorator, ast.Name):
            return decorator.id in ["atlasvibe", "atlasvibe_node"]
        elif isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name):
            return decorator.func.id in ["atlasvibe", "atlasvibe_node"]
        return False

    def _is_invalid_type(self, type_str: str) -> bool:
        """Check if a type annotation string is invalid."""
        # This is a simple check - could be expanded
        invalid_patterns = [
            r"^\d",  # Starts with digit
            r"\s",  # Contains whitespace (except in Union, etc.)
        ]
        return any(re.search(pattern, type_str) for pattern in invalid_patterns)

    def _get_syntax_error_suggestion(self, msg: str) -> Optional[str]:
        """Get suggestion for common syntax errors."""
        suggestions = {
            "invalid syntax": "Check for missing colons, parentheses, or quotes",
            "unexpected EOF": "Check for unclosed parentheses, brackets, or quotes",
            "unexpected indent": "Check indentation - use consistent spaces or tabs",
            "unindent does not match": "Fix indentation to match the block level",
        }

        for key, suggestion in suggestions.items():
            if key in msg.lower():
                return suggestion
        return None

    def _validate_complexity(self, tree: ast.AST) -> List[ValidationError]:
        """Validate code complexity."""
        errors = []
        visitor = ComplexityVisitor()
        visitor.visit(tree)

        for func_info in visitor.complex_functions:
            if func_info["complexity"] > 10:  # McCabe complexity threshold
                errors.append(
                    ValidationError(
                        line=func_info["line"],
                        column=0,
                        message=f"Function '{func_info['name']}' is too complex (complexity: {func_info['complexity']})",
                        severity="warning",
                        category="complexity",
                        suggestion="Consider breaking this function into smaller functions",
                    )
                )

        return errors

    def _validate_missing_return_types(self, tree: ast.AST) -> List[ValidationError]:
        """Check for missing return type annotations."""
        errors = []
        visitor = FunctionVisitor()
        visitor.visit(tree)

        for func in visitor.functions:
            # Skip special methods
            if func.name.startswith("__") and func.name.endswith("__"):
                continue

            # Check if function has return statement but no return type
            has_return = any(
                isinstance(node, ast.Return) and node.value is not None
                for node in ast.walk(func)
            )

            if has_return and not func.returns:
                errors.append(
                    ValidationError(
                        line=func.lineno,
                        column=func.col_offset,
                        message=f"Function '{func.name}' is missing return type annotation",
                        severity="warning",
                        category="type",
                        suggestion=f"Add return type annotation: def {func.name}(...) -> ReturnType:",
                    )
                )

        return errors


class ComplexityVisitor(ast.NodeVisitor):
    """Calculate cyclomatic complexity of functions."""

    def __init__(self):
        self.complex_functions = []
        self.current_complexity = 0
        self.current_function = None

    def visit_FunctionDef(self, node):
        # Save previous state
        prev_complexity = self.current_complexity
        prev_function = self.current_function

        # Start new function
        self.current_complexity = 1  # Base complexity
        self.current_function = node.name

        # Visit function body
        self.generic_visit(node)

        # Record complexity
        self.complex_functions.append(
            {
                "name": node.name,
                "line": node.lineno,
                "complexity": self.current_complexity,
            }
        )

        # Restore previous state
        self.current_complexity = prev_complexity
        self.current_function = prev_function

    def visit_If(self, node):
        self.current_complexity += 1
        self.generic_visit(node)

    def visit_While(self, node):
        self.current_complexity += 1
        self.generic_visit(node)

    def visit_For(self, node):
        self.current_complexity += 1
        self.generic_visit(node)

    def visit_ExceptHandler(self, node):
        self.current_complexity += 1
        self.generic_visit(node)

    def visit_With(self, node):
        self.current_complexity += 1
        self.generic_visit(node)

    def visit_Assert(self, node):
        self.current_complexity += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node):
        # Add complexity for each additional condition in and/or
        self.current_complexity += len(node.values) - 1
        self.generic_visit(node)


class ImportVisitor(ast.NodeVisitor):
    """AST visitor to collect import information."""

    def __init__(self):
        self.imports = []

    def visit_Import(self, node):
        for alias in node.names:
            self.imports.append(
                {"module": alias.name, "line": node.lineno, "col": node.col_offset}
            )
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module:
            self.imports.append(
                {"module": node.module, "line": node.lineno, "col": node.col_offset}
            )
        self.generic_visit(node)


class DecoratorVisitor(ast.NodeVisitor):
    """AST visitor to collect decorator information."""

    def __init__(self):
        self.decorated_functions = []

    def visit_FunctionDef(self, node):
        decorators = []
        for dec in node.decorator_list:
            if isinstance(dec, ast.Name):
                decorators.append(dec.id)
            elif isinstance(dec, ast.Call) and isinstance(dec.func, ast.Name):
                decorators.append(dec.func.id)

        if decorators:
            self.decorated_functions.append(
                {
                    "name": node.name,
                    "decorators": decorators,
                    "line": node.lineno,
                    "col": node.col_offset,
                }
            )

        self.generic_visit(node)


class FunctionVisitor(ast.NodeVisitor):
    """AST visitor to collect function information."""

    def __init__(self):
        self.functions = []

    def visit_FunctionDef(self, node):
        self.functions.append(node)
        self.generic_visit(node)


class VariableVisitor(ast.NodeVisitor):
    """AST visitor to track variable definitions and usage."""

    def __init__(self):
        self.defined_names = set()
        self.used_names = set()
        self.variable_uses = []

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Store):
            self.defined_names.add(node.id)
        elif isinstance(node.ctx, ast.Load):
            self.used_names.add(node.id)
            self.variable_uses.append(
                {"name": node.id, "line": node.lineno, "col": node.col_offset}
            )
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        # Function name is defined
        self.defined_names.add(node.name)
        # Function parameters are defined within the function
        for arg in node.args.args:
            self.defined_names.add(arg.arg)
        self.generic_visit(node)

    def visit_Import(self, node):
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            self.defined_names.add(name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            self.defined_names.add(name)
        self.generic_visit(node)


class TypeAnnotationVisitor(ast.NodeVisitor):
    """AST visitor to collect type annotations."""

    def __init__(self):
        self.annotations = []

    def visit_AnnAssign(self, node):
        if node.annotation:
            self.annotations.append(
                {
                    "annotation": ast.unparse(node.annotation),
                    "line": node.lineno,
                    "col": node.col_offset,
                }
            )
        self.generic_visit(node)

    def visit_arg(self, node):
        if node.annotation:
            self.annotations.append(
                {
                    "annotation": ast.unparse(node.annotation),
                    "line": node.lineno if hasattr(node, "lineno") else 0,
                    "col": node.col_offset if hasattr(node, "col_offset") else 0,
                }
            )
        self.generic_visit(node)


# Utility functions for the API


def validate_python_code(
    code: str, filename: str = "<unknown>", project_path: Optional[str] = None
) -> Dict[str, Any]:
    """Validate Python code and return results in API format.

    Args:
        code: Python code to validate.
        filename: Name of the file being validated.
        project_path: Path to the project directory.

    Returns:
        Dictionary with validation results.
    """
    validator = PythonValidator(Path(project_path) if project_path else None)
    errors = validator.validate_code(code, filename)

    return {
        "valid": len([e for e in errors if e.severity == "error"]) == 0,
        "errors": [
            {
                "line": e.line,
                "column": e.column,
                "message": e.message,
                "severity": e.severity,
                "category": e.category,
                "suggestion": e.suggestion,
            }
            for e in errors
        ],
    }

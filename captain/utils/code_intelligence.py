#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Initial implementation of code intelligence for AtlasVibe blocks
# - Symbol extraction (functions, classes, variables)
# - Type hint analysis
# - Context-aware completion generation
# - Docstring parsing for parameter information
#

"""
Code intelligence for AtlasVibe blocks.

This module provides code analysis and completion generation including:
- Symbol extraction and indexing
- Type analysis
- Context-aware completions
- Parameter hints
- Docstring information extraction
"""

import ast
import builtins
import inspect
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class Symbol:
    """Represents a code symbol (function, class, variable, etc.).

    Args:
        name: Symbol name.
        kind: Type of symbol ('function', 'class', 'variable', etc.).
        line: Line number where defined.
        column: Column number where defined.
        signature: Function/method signature if applicable.
        docstring: Documentation string if available.
        type_hint: Type annotation if available.
    """

    name: str
    kind: str
    line: int
    column: int
    signature: Optional[str] = None
    docstring: Optional[str] = None
    type_hint: Optional[str] = None


@dataclass
class CompletionItem:
    """Represents a code completion suggestion.

    Args:
        label: The text to show in completion list.
        kind: Type of completion ('function', 'class', 'variable', etc.).
        insert_text: Text to actually insert.
        detail: Additional information (e.g., type signature).
        documentation: Full documentation/docstring.
        sort_text: Text used for sorting (lower values appear first).
    """

    label: str
    kind: str
    insert_text: str
    detail: Optional[str] = None
    documentation: Optional[str] = None
    sort_text: Optional[str] = None


class CodeIntelligence:
    """Provides code intelligence features for AtlasVibe blocks."""

    def __init__(self, project_path: Optional[Path] = None):
        """Initialize code intelligence.

        Args:
            project_path: Path to the project directory.
        """
        self.project_path = project_path
        self._init_builtin_completions()
        self._init_atlasvibe_completions()

    def _init_builtin_completions(self):
        """Initialize Python builtin completions."""
        self.builtin_completions = []

        # Add Python keywords
        keywords = [
            "and",
            "as",
            "assert",
            "async",
            "await",
            "break",
            "class",
            "continue",
            "def",
            "del",
            "elif",
            "else",
            "except",
            "False",
            "finally",
            "for",
            "from",
            "global",
            "if",
            "import",
            "in",
            "is",
            "lambda",
            "None",
            "nonlocal",
            "not",
            "or",
            "pass",
            "raise",
            "return",
            "True",
            "try",
            "while",
            "with",
            "yield",
        ]

        for kw in keywords:
            self.builtin_completions.append(
                CompletionItem(
                    label=kw,
                    kind="keyword",
                    insert_text=kw,
                    sort_text=f"0_{kw}",  # Keywords first
                )
            )

        # Add builtin functions
        for name in dir(builtins):
            if not name.startswith("_"):
                obj = getattr(builtins, name)
                if callable(obj):
                    sig = self._get_signature(obj)
                    self.builtin_completions.append(
                        CompletionItem(
                            label=name,
                            kind="function",
                            insert_text=f"{name}($0)",
                            detail=sig,
                            documentation=inspect.getdoc(obj),
                            sort_text=f"1_{name}",
                        )
                    )
                elif isinstance(obj, type):
                    self.builtin_completions.append(
                        CompletionItem(
                            label=name,
                            kind="class",
                            insert_text=f"{name}($0)",
                            detail=f"class {name}",
                            documentation=inspect.getdoc(obj),
                            sort_text=f"1_{name}",
                        )
                    )

    def _init_atlasvibe_completions(self):
        """Initialize AtlasVibe-specific completions."""
        self.atlasvibe_completions = [
            # Decorators
            CompletionItem(
                label="@atlasvibe",
                kind="decorator",
                insert_text='@atlasvibe(deps=["$0"])\ndef ${1:function_name}(${2:params}):\n    """${3:description}\n    \n    Parameters\n    ----------\n    ${4:param} : ${5:type}\n        ${6:param_description}\n    \n    Returns\n    -------\n    ${7:return_type}\n        ${8:return_description}\n    """\n    ${9:pass}',
                detail="AtlasVibe block decorator",
                documentation="Decorator for defining an AtlasVibe block function",
                sort_text="0_@atlasvibe",
            ),
            # Data types
            CompletionItem(
                label="DataContainer",
                kind="class",
                insert_text="DataContainer",
                detail="from atlasvibe import DataContainer",
                documentation="Base class for AtlasVibe data containers",
                sort_text="0_DataContainer",
            ),
            CompletionItem(
                label="Scalar",
                kind="class",
                insert_text="Scalar",
                detail="from atlasvibe import Scalar",
                documentation="Container for scalar values",
                sort_text="0_Scalar",
            ),
            CompletionItem(
                label="Vector",
                kind="class",
                insert_text="Vector",
                detail="from atlasvibe import Vector",
                documentation="Container for 1D arrays/vectors",
                sort_text="0_Vector",
            ),
            CompletionItem(
                label="Matrix",
                kind="class",
                insert_text="Matrix",
                detail="from atlasvibe import Matrix",
                documentation="Container for 2D arrays/matrices",
                sort_text="0_Matrix",
            ),
            CompletionItem(
                label="DataFrame",
                kind="class",
                insert_text="DataFrame",
                detail="from atlasvibe import DataFrame",
                documentation="Container for pandas DataFrames",
                sort_text="0_DataFrame",
            ),
            CompletionItem(
                label="OrderedPair",
                kind="class",
                insert_text="OrderedPair",
                detail="from atlasvibe import OrderedPair",
                documentation="Container for x,y coordinate pairs",
                sort_text="0_OrderedPair",
            ),
            CompletionItem(
                label="Surface",
                kind="class",
                insert_text="Surface",
                detail="from atlasvibe import Surface",
                documentation="Container for 3D surface data",
                sort_text="0_Surface",
            ),
            # Common imports
            CompletionItem(
                label="import numpy as np",
                kind="import",
                insert_text="import numpy as np",
                detail="Import NumPy library",
                sort_text="0_import_numpy",
            ),
            CompletionItem(
                label="import pandas as pd",
                kind="import",
                insert_text="import pandas as pd",
                detail="Import pandas library",
                sort_text="0_import_pandas",
            ),
            CompletionItem(
                label="from atlasvibe import",
                kind="import",
                insert_text="from atlasvibe import ${0:DataContainer}",
                detail="Import from AtlasVibe",
                sort_text="0_from_atlasvibe",
            ),
        ]

    def extract_symbols(self, code: str) -> List[Symbol]:
        """Extract all symbols from Python code.

        Args:
            code: Python source code.

        Returns:
            List of Symbol objects found in the code.
        """
        symbols = []

        try:
            tree = ast.parse(code)
        except SyntaxError:
            return symbols

        visitor = SymbolVisitor()
        visitor.visit(tree)

        return visitor.symbols

    def get_completions(
        self, code: str, line: int, column: int, trigger_char: Optional[str] = None
    ) -> List[CompletionItem]:
        """Get context-aware completions for the given position.

        Args:
            code: Python source code.
            line: Current line number (1-indexed).
            column: Current column number (0-indexed).
            trigger_char: Character that triggered completion (e.g., '.').

        Returns:
            List of completion items appropriate for the context.
        """
        completions = []

        # Get context at cursor position
        context = self._get_context(code, line, column)

        if trigger_char == ".":
            # Member access completion
            completions.extend(self._get_member_completions(context))
        elif context.in_import:
            # Import completion
            completions.extend(self._get_import_completions(context))
        elif context.in_type_hint:
            # Type hint completion
            completions.extend(self._get_type_completions(context))
        else:
            # General completion
            completions.extend(self.builtin_completions)
            completions.extend(self.atlasvibe_completions)

            # Add symbols from current code
            symbols = self.extract_symbols(code)
            for sym in symbols:
                if sym.kind == "function":
                    completions.append(
                        CompletionItem(
                            label=sym.name,
                            kind=sym.kind,
                            insert_text=f"{sym.name}($0)",
                            detail=sym.signature,
                            documentation=sym.docstring,
                            sort_text=f"2_{sym.name}",
                        )
                    )
                else:
                    completions.append(
                        CompletionItem(
                            label=sym.name,
                            kind=sym.kind,
                            insert_text=sym.name,
                            detail=sym.type_hint,
                            documentation=sym.docstring,
                            sort_text=f"2_{sym.name}",
                        )
                    )

        # Filter by prefix if any
        if context.prefix:
            completions = [
                c
                for c in completions
                if c.label.lower().startswith(context.prefix.lower())
            ]

        # Sort and limit
        completions.sort(key=lambda c: (c.sort_text or c.label))
        return completions[:100]  # Limit to 100 items

    def get_hover_info(
        self, code: str, line: int, column: int
    ) -> Optional[Dict[str, Any]]:
        """Get hover information for symbol at position.

        Args:
            code: Python source code.
            line: Line number (1-indexed).
            column: Column number (0-indexed).

        Returns:
            Dictionary with hover information or None.
        """
        # Find symbol at position
        symbol = self._find_symbol_at_position(code, line, column)
        if not symbol:
            return None

        return {
            "name": symbol.name,
            "kind": symbol.kind,
            "signature": symbol.signature,
            "documentation": symbol.docstring,
            "type": symbol.type_hint,
        }

    def _get_signature(self, obj: Any) -> Optional[str]:
        """Get function signature as string."""
        try:
            sig = inspect.signature(obj)
            return f"{obj.__name__}{sig}"
        except (ValueError, TypeError):
            return None

    def _get_context(self, code: str, line: int, column: int) -> "CompletionContext":
        """Analyze context at cursor position."""
        # This is a simplified implementation
        lines = code.split("\n")
        if line <= 0 or line > len(lines):
            return CompletionContext()

        current_line = lines[line - 1]
        before_cursor = current_line[:column]

        context = CompletionContext()

        # Check if we're in an import statement
        if re.match(r"^\s*(from|import)\s+\S*$", before_cursor):
            context.in_import = True

        # Check if we're in a type hint
        if ":" in before_cursor and "#" not in before_cursor:
            # Simple heuristic - after : and before =
            after_colon = before_cursor.split(":")[-1]
            if "=" not in after_colon:
                context.in_type_hint = True

        # Extract prefix (word being typed)
        match = re.search(r"(\w+)$", before_cursor)
        if match:
            context.prefix = match.group(1)

        # Extract object for member access
        match = re.search(r"(\w+)\.$", before_cursor)
        if match:
            context.object_name = match.group(1)

        return context

    def _get_member_completions(
        self, context: "CompletionContext"
    ) -> List[CompletionItem]:
        """Get member completions for object access."""
        completions = []

        if context.object_name == "np":
            # NumPy completions
            numpy_funcs = [
                "array",
                "zeros",
                "ones",
                "arange",
                "linspace",
                "random",
                "sum",
                "mean",
                "std",
                "min",
                "max",
                "argmin",
                "argmax",
                "dot",
                "cross",
                "transpose",
                "reshape",
                "concatenate",
            ]
            for func in numpy_funcs:
                completions.append(
                    CompletionItem(
                        label=func,
                        kind="function",
                        insert_text=f"{func}($0)",
                        detail=f"np.{func}",
                        sort_text=f"0_{func}",
                    )
                )

        elif context.object_name == "pd":
            # Pandas completions
            pandas_items = [
                ("DataFrame", "class", "DataFrame($0)"),
                ("Series", "class", "Series($0)"),
                ("read_csv", "function", "read_csv('$0')"),
                ("read_excel", "function", "read_excel('$0')"),
                ("concat", "function", "concat([$0])"),
            ]
            for name, kind, insert in pandas_items:
                completions.append(
                    CompletionItem(
                        label=name,
                        kind=kind,
                        insert_text=insert,
                        detail=f"pd.{name}",
                        sort_text=f"0_{name}",
                    )
                )

        return completions

    def _get_import_completions(
        self, context: "CompletionContext"
    ) -> List[CompletionItem]:
        """Get import statement completions."""
        return [
            CompletionItem(
                label="numpy",
                kind="module",
                insert_text="numpy as np",
                detail="import numpy as np",
                sort_text="0_numpy",
            ),
            CompletionItem(
                label="pandas",
                kind="module",
                insert_text="pandas as pd",
                detail="import pandas as pd",
                sort_text="0_pandas",
            ),
            CompletionItem(
                label="atlasvibe",
                kind="module",
                insert_text="atlasvibe",
                detail="import atlasvibe",
                sort_text="0_atlasvibe",
            ),
        ]

    def _get_type_completions(
        self, context: "CompletionContext"
    ) -> List[CompletionItem]:
        """Get type hint completions."""
        types = [
            "int",
            "float",
            "str",
            "bool",
            "list",
            "dict",
            "tuple",
            "set",
            "List",
            "Dict",
            "Tuple",
            "Set",
            "Optional",
            "Union",
            "Any",
            "Scalar",
            "Vector",
            "Matrix",
            "DataFrame",
            "OrderedPair",
            "Surface",
        ]

        completions = []
        for t in types:
            completions.append(
                CompletionItem(
                    label=t,
                    kind="type",
                    insert_text=t,
                    detail=f"Type: {t}",
                    sort_text=f"0_{t}",
                )
            )

        return completions

    def _find_symbol_at_position(
        self, code: str, line: int, column: int
    ) -> Optional[Symbol]:
        """Find symbol at the given position."""
        symbols = self.extract_symbols(code)

        # Simple implementation - find symbol name at position
        lines = code.split("\n")
        if line <= 0 or line > len(lines):
            return None

        current_line = lines[line - 1]

        # Extract word at position
        start = column
        while (
            start > 0
            and current_line[start - 1].isalnum()
            or current_line[start - 1] == "_"
        ):
            start -= 1

        end = column
        while end < len(current_line) and (
            current_line[end].isalnum() or current_line[end] == "_"
        ):
            end += 1

        word = current_line[start:end]

        # Find matching symbol
        for sym in symbols:
            if sym.name == word:
                return sym

        return None


@dataclass
class CompletionContext:
    """Context information at cursor position."""

    in_import: bool = False
    in_type_hint: bool = False
    prefix: Optional[str] = None
    object_name: Optional[str] = None


class SymbolVisitor(ast.NodeVisitor):
    """AST visitor to extract symbols."""

    def __init__(self):
        self.symbols = []

    def visit_FunctionDef(self, node):
        # Extract function signature
        args = []
        for arg in node.args.args:
            arg_str = arg.arg
            if arg.annotation:
                arg_str += f": {ast.unparse(arg.annotation)}"
            args.append(arg_str)

        signature = f"({', '.join(args)})"
        if node.returns:
            signature += f" -> {ast.unparse(node.returns)}"

        self.symbols.append(
            Symbol(
                name=node.name,
                kind="function",
                line=node.lineno,
                column=node.col_offset,
                signature=signature,
                docstring=ast.get_docstring(node),
                type_hint=ast.unparse(node.returns) if node.returns else None,
            )
        )

        self.generic_visit(node)

    def visit_ClassDef(self, node):
        self.symbols.append(
            Symbol(
                name=node.name,
                kind="class",
                line=node.lineno,
                column=node.col_offset,
                docstring=ast.get_docstring(node),
            )
        )

        self.generic_visit(node)

    def visit_Assign(self, node):
        # Simple variable assignments
        for target in node.targets:
            if isinstance(target, ast.Name):
                self.symbols.append(
                    Symbol(
                        name=target.id,
                        kind="variable",
                        line=target.lineno,
                        column=target.col_offset,
                    )
                )

        self.generic_visit(node)

    def visit_AnnAssign(self, node):
        # Annotated assignments
        if isinstance(node.target, ast.Name):
            self.symbols.append(
                Symbol(
                    name=node.target.id,
                    kind="variable",
                    line=node.target.lineno,
                    column=node.target.col_offset,
                    type_hint=ast.unparse(node.annotation) if node.annotation else None,
                )
            )

        self.generic_visit(node)


# API utility functions


def get_completions(
    code: str,
    line: int,
    column: int,
    trigger_char: Optional[str] = None,
    project_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Get code completions in API format.

    Args:
        code: Python source code.
        line: Line number (1-indexed).
        column: Column number (0-indexed).
        trigger_char: Character that triggered completion.
        project_path: Path to project directory.

    Returns:
        List of completion items as dictionaries.
    """
    intelligence = CodeIntelligence(Path(project_path) if project_path else None)
    completions = intelligence.get_completions(code, line, column, trigger_char)

    return [
        {
            "label": c.label,
            "kind": c.kind,
            "insertText": c.insert_text,
            "detail": c.detail,
            "documentation": c.documentation,
        }
        for c in completions
    ]


def get_hover_info(
    code: str, line: int, column: int, project_path: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Get hover information in API format.

    Args:
        code: Python source code.
        line: Line number (1-indexed).
        column: Column number (0-indexed).
        project_path: Path to project directory.

    Returns:
        Hover information dictionary or None.
    """
    intelligence = CodeIntelligence(Path(project_path) if project_path else None)
    return intelligence.get_hover_info(code, line, column)

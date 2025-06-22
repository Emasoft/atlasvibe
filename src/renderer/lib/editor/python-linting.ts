/*
 * Copyright (c) 2024 Emasoft
 *
 * This file is part of AtlasVibe, which is based on Flojoy Studio
 * Original Copyright (c) 2023-2024 Flojoy
 *
 * SPDX-License-Identifier: MIT
 * See the LICENSE file for details.
 */

import { Diagnostic } from "@codemirror/lint";
import { EditorView } from "@codemirror/view";
import { syntaxTree } from "@codemirror/language";

/**
 * Check if a docstring has the required NumPy-style format
 */
export function hasValidDocstringFormat(docstring: string): boolean {
  const hasParameters = /Parameters\s*\n\s*-+/.test(docstring);
  const hasReturns = /Returns\s*\n\s*-+/.test(docstring);
  return hasParameters && hasReturns;
}

/**
 * Validates NumPy-style docstrings in Python code
 */
export function validateDocstring(docstring: string, docstringStart: number): Diagnostic[] {
  const diagnostics: Diagnostic[] = [];

  // Check for required sections
  const hasParameters = /^\s*Parameters\s*$/m.test(docstring);
  const hasReturns = /^\s*Returns\s*$/m.test(docstring);

  // Check for proper formatting with dashes
  const hasParametersDashes = /Parameters\s*\n\s*-+/m.test(docstring);
  const hasReturnsDashes = /Returns\s*\n\s*-+/m.test(docstring);

  if (!hasParameters || !hasReturns) {
    diagnostics.push({
      from: docstringStart,
      to: docstringStart + docstring.length,
      severity: "warning",
      message: "AtlasVibe blocks require NumPy-style docstrings with Parameters and Returns sections",
    });
  } else if (!hasParametersDashes || !hasReturnsDashes) {
    diagnostics.push({
      from: docstringStart,
      to: docstringStart + docstring.length,
      severity: "warning",
      message: "Parameters and Returns sections must be followed by dashes (------)",
    });
  }

  // Check parameter format (name : type)
  const parameterSection = docstring.match(/Parameters\s*\n\s*-+\s*\n([\s\S]*?)(?=\n\s*Returns|$)/);
  if (parameterSection) {
    const paramContent = parameterSection[1];
    const paramStartOffset = docstring.indexOf(paramContent);
    const paramLines = paramContent.split('\n');

    let currentOffset = paramStartOffset;
    paramLines.forEach((line) => {
      if (line.trim() && !line.match(/^\s*\w+\s*:\s*[\w[\]|\s,]+/) && !line.match(/^\s*Description/)) {
        diagnostics.push({
          from: docstringStart + currentOffset,
          to: docstringStart + currentOffset + line.length,
          severity: "error",
          message: `Invalid parameter format. Expected: "name : type" format`,
        });
      }
      currentOffset += line.length + 1; // +1 for newline
    });
  }

  return diagnostics;
}

/**
 * Basic Python syntax validation
 */
export async function pythonLinter(view: EditorView): Promise<Diagnostic[]> {
  const diagnostics: Diagnostic[] = [];
  const doc = view.state.doc;

  try {
    // Basic syntax checks
    const tree = syntaxTree(view.state);

    // Check for common Python errors
    tree.iterate({
      enter(node) {
        const text = doc.sliceString(node.from, node.to);

        // Check for tabs vs spaces (Python is sensitive to this)
        if (node.name === "Body") {
          const lines = text.split('\n');
          let usesSpaces = false;
          let usesTabs = false;

          lines.forEach((line) => {
            if (line.match(/^ +/)) usesSpaces = true;
            if (line.match(/^\t+/)) usesTabs = true;
          });

          if (usesSpaces && usesTabs) {
            diagnostics.push({
              from: node.from,
              to: node.to,
              severity: "error",
              message: "Mixed tabs and spaces in indentation",
            });
          }
        }

        // Check for missing colons after def, if, for, etc.
        if (node.name === "FunctionDefinition" || node.name === "IfStatement" ||
            node.name === "ForStatement" || node.name === "WhileStatement") {
          const lastChar = text.trim().slice(-1);
          if (lastChar !== ':') {
            diagnostics.push({
              from: node.to - 1,
              to: node.to,
              severity: "error",
              message: `Missing ':' after ${node.name.replace("Statement", "").toLowerCase()}`,
            });
          }
        }

        // Check docstrings in functions
        if (node.name === "FunctionDefinition") {
          const functionText = doc.sliceString(node.from, node.to);
          const docstringMatch = functionText.match(/"""([\s\S]*?)"""/);

          if (docstringMatch) {
            const docstring = docstringMatch[1];
            const docstringStart = node.from + functionText.indexOf('"""');

            // Check if this is an AtlasVibe block function
            const hasAtlasVibeDecorator = functionText.includes("@atlasvibe");

            if (hasAtlasVibeDecorator) {
              const docstringDiagnostics = validateDocstring(docstring, docstringStart);
              diagnostics.push(...docstringDiagnostics);
            }
          } else if (functionText.includes("@atlasvibe")) {
            // AtlasVibe function without docstring
            diagnostics.push({
              from: node.from,
              to: node.from + 50,
              severity: "error",
              message: "AtlasVibe blocks require a docstring with Parameters and Returns sections",
            });
          }
        }
      }
    });

  } catch (error) {
    // Silently ignore parsing errors and return diagnostics collected so far
  }

  return diagnostics;
}

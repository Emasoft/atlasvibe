import { Diagnostic } from "@codemirror/lint";
import { EditorView } from "@codemirror/view";
import { syntaxTree } from "@codemirror/language";
import { Text } from "@codemirror/state";

/**
 * Validates NumPy-style docstrings in Python code
 */
export function validateDocstring(docstring: string, startLine: number): Diagnostic[] {
  const diagnostics: Diagnostic[] = [];
  const lines = docstring.split('\n');
  
  // Check for required sections
  const hasParameters = /^\s*Parameters\s*$/m.test(docstring);
  const hasReturns = /^\s*Returns\s*$/m.test(docstring);
  
  // Check for proper formatting
  const parameterSection = docstring.match(/Parameters\s*\n\s*-+\s*\n([\s\S]*?)(?=\n\s*\n|Returns|$)/);
  const returnsSection = docstring.match(/Returns\s*\n\s*-+\s*\n([\s\S]*?)(?=\n\s*\n|$)/);
  
  if (!hasParameters && !hasReturns) {
    diagnostics.push({
      from: 0,
      to: 0,
      severity: "warning",
      message: "AtlasVibe blocks require NumPy-style docstrings with Parameters and Returns sections",
    });
  }
  
  // Check parameter format (name : type)
  if (parameterSection) {
    const paramLines = parameterSection[1].split('\n');
    paramLines.forEach((line, idx) => {
      if (line.trim() && !line.match(/^\s*\w+\s*:\s*[\w\[\]\|]+/)) {
        diagnostics.push({
          from: 0,
          to: 0,
          severity: "error",
          message: `Invalid parameter format. Expected: "name : type". Got: "${line.trim()}"`,
        });
      }
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
          
          lines.forEach((line, idx) => {
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
            const startLine = doc.lineAt(docstringStart).number;
            
            // Check if this is an AtlasVibe block function
            const hasAtlasVibeDecorator = functionText.includes("@atlasvibe");
            
            if (hasAtlasVibeDecorator) {
              const docstringDiagnostics = validateDocstring(docstring, startLine);
              docstringDiagnostics.forEach(diag => {
                diagnostics.push({
                  ...diag,
                  from: docstringStart + diag.from,
                  to: docstringStart + diag.to || docstringStart + docstring.length,
                });
              });
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
    console.error("Error in Python linter:", error);
  }
  
  return diagnostics;
}

/**
 * Check for Python syntax errors using a simple regex-based approach
 */
export function checkPythonSyntax(code: string): Diagnostic[] {
  const diagnostics: Diagnostic[] = [];
  const lines = code.split('\n');
  
  lines.forEach((line, idx) => {
    // Check for unclosed brackets
    const openBrackets = (line.match(/[\[\({]/g) || []).length;
    const closeBrackets = (line.match(/[\]\)}]/g) || []).length;
    
    if (openBrackets !== closeBrackets && !line.trim().endsWith('\\')) {
      diagnostics.push({
        from: idx * 100, // Rough estimate
        to: (idx + 1) * 100,
        severity: "error",
        message: "Unclosed bracket",
      });
    }
    
    // Check for invalid indentation increase
    if (idx > 0) {
      const prevIndent = lines[idx - 1].match(/^[\s]*/)?.[0].length || 0;
      const currIndent = line.match(/^[\s]*/)?.[0].length || 0;
      
      if (currIndent > prevIndent && currIndent - prevIndent > 4 && line.trim()) {
        diagnostics.push({
          from: idx * 100,
          to: (idx + 1) * 100,
          severity: "warning",
          message: "Unusual indentation increase",
        });
      }
    }
  });
  
  return diagnostics;
}
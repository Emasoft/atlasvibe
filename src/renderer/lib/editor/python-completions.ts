import { CompletionContext, CompletionResult, Completion } from "@codemirror/autocomplete";

// Common AtlasVibe imports and patterns
const ATLASVIBE_IMPORTS = [
  "from pkgs.atlasvibe.atlasvibe.atlasvibe_python import atlasvibe",
  "from pkgs.atlasvibe.atlasvibe.data_container import Scalar, Vector, Matrix, DataFrame, OrderedPair, OrderedTriple",
  "from pkgs.atlasvibe.atlasvibe.parameter_types import File, Directory",
  "import numpy as np",
  "import pandas as pd",
];

const ATLASVIBE_DECORATORS = [
  { label: "@atlasvibe", type: "function", detail: "AtlasVibe block decorator" },
  { label: "@atlasvibe_node", type: "function", detail: "AtlasVibe node decorator" },
];

const DATA_CONTAINER_TYPES = [
  { label: "Scalar", type: "class", detail: "Single value container" },
  { label: "Vector", type: "class", detail: "1D array container" },
  { label: "Matrix", type: "class", detail: "2D array container" },
  { label: "DataFrame", type: "class", detail: "Pandas DataFrame container" },
  { label: "OrderedPair", type: "class", detail: "X-Y pair container" },
  { label: "OrderedTriple", type: "class", detail: "X-Y-Z triple container" },
];

const PYTHON_KEYWORDS = [
  "def", "class", "if", "else", "elif", "for", "while", "return", "import", "from",
  "try", "except", "finally", "with", "as", "pass", "break", "continue",
  "lambda", "yield", "global", "nonlocal", "assert", "del", "in", "is", "not",
  "and", "or", "True", "False", "None"
].map(kw => ({ label: kw, type: "keyword" }));

const NUMPY_COMPLETIONS = [
  { label: "np.array", type: "function", detail: "Create numpy array" },
  { label: "np.zeros", type: "function", detail: "Array of zeros" },
  { label: "np.ones", type: "function", detail: "Array of ones" },
  { label: "np.arange", type: "function", detail: "Array with range of values" },
  { label: "np.linspace", type: "function", detail: "Evenly spaced values" },
  { label: "np.random.rand", type: "function", detail: "Random values [0,1)" },
  { label: "np.mean", type: "function", detail: "Compute mean" },
  { label: "np.std", type: "function", detail: "Compute standard deviation" },
  { label: "np.sum", type: "function", detail: "Sum of array elements" },
];

/**
 * Docstring template generator
 */
function generateDocstringTemplate(context: CompletionContext): Completion | null {
  const line = context.state.doc.lineAt(context.pos);
  const beforeCursor = line.text.slice(0, context.pos - line.from);
  
  // Check if we're right after a function definition
  if (beforeCursor.trim().endsWith(':')) {
    const match = beforeCursor.match(/def\s+(\w+)\s*\((.*?)\)/);
    if (match) {
      const [, , params] = match;
      const paramList = params.split(',').map(p => p.trim().split(':')[0].trim()).filter(p => p && p !== 'self');
      
      let docstring = '"""\n    Brief description.\n    \n';
      
      if (paramList.length > 0) {
        docstring += '    Parameters\n    ----------\n';
        paramList.forEach(param => {
          docstring += `    ${param} : type\n        Description of ${param}.\n`;
        });
        docstring += '    \n';
      }
      
      docstring += '    Returns\n    -------\n    type\n        Description of return value.\n    """';
      
      return {
        label: '"""docstring"""',
        type: "snippet",
        detail: "NumPy-style docstring",
        apply: docstring,
      };
    }
  }
  
  return null;
}

/**
 * Python autocompletion provider
 */
export function pythonCompletions(context: CompletionContext): CompletionResult | null {
  const word = context.matchBefore(/\w*/);
  if (!word || (word.from === word.to && !context.explicit)) {
    return null;
  }

  const completions: Completion[] = [];
  
  // Check if we need a docstring
  const docstringCompletion = generateDocstringTemplate(context);
  if (docstringCompletion) {
    completions.push(docstringCompletion);
  }
  
  // Get the current line
  const line = context.state.doc.lineAt(context.pos);
  const beforeCursor = line.text.slice(0, context.pos - line.from);
  
  // Import completions
  if (beforeCursor.match(/^(from|import)\s+/)) {
    ATLASVIBE_IMPORTS.forEach(imp => {
      completions.push({
        label: imp,
        type: "text",
        detail: "AtlasVibe import",
      });
    });
  }
  
  // Decorator completions
  if (beforeCursor.match(/^@/)) {
    completions.push(...ATLASVIBE_DECORATORS);
  }
  
  // Type hints after colon
  if (beforeCursor.includes(':') && beforeCursor.match(/\w+\s*:\s*$/)) {
    completions.push(...DATA_CONTAINER_TYPES);
    completions.push(
      { label: "list", type: "class" },
      { label: "dict", type: "class" },
      { label: "str", type: "class" },
      { label: "int", type: "class" },
      { label: "float", type: "class" },
      { label: "bool", type: "class" },
      { label: "Optional", type: "class", detail: "from typing" },
      { label: "Union", type: "class", detail: "from typing" },
      { label: "List", type: "class", detail: "from typing" },
      { label: "Dict", type: "class", detail: "from typing" },
      { label: "Literal", type: "class", detail: "from typing" },
    );
  }
  
  // NumPy completions after np.
  if (beforeCursor.endsWith('np.')) {
    completions.push(...NUMPY_COMPLETIONS);
  }
  
  // Data container completions  
  if (word) {
    completions.push(...DATA_CONTAINER_TYPES);
    completions.push(...PYTHON_KEYWORDS);
  }
  
  return {
    from: word.from,
    options: completions,
  };
}

/**
 * AtlasVibe-specific snippet completions
 */
export const atlasvibeSnippets: Completion[] = [
  {
    label: "atlasvibe_block",
    type: "snippet",
    detail: "Create AtlasVibe block template",
    apply: `from pkgs.atlasvibe.atlasvibe.atlasvibe_python import atlasvibe
from pkgs.atlasvibe.atlasvibe.data_container import Scalar, Vector, OrderedPair

@atlasvibe
def BLOCK_NAME(input_a: Scalar | Vector, input_b: Scalar | Vector) -> Scalar | Vector:
    """
    Brief description of the block.
    
    Parameters
    ----------
    input_a : Scalar | Vector
        Description of input_a.
    input_b : Scalar | Vector  
        Description of input_b.
        
    Returns
    -------
    Scalar | Vector
        Description of the output.
    """
    # Implementation here
    pass`,
  },
  {
    label: "numpy_docstring",
    type: "snippet", 
    detail: "NumPy-style docstring template",
    apply: `"""
    Brief description.
    
    Parameters
    ----------
    param1 : type
        Description of param1.
    param2 : type
        Description of param2.
        
    Returns
    -------
    type
        Description of return value.
    """`,
  }
];
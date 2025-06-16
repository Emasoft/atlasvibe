#!/usr/bin/env python3
"""Add docstrings to test functions that lack them."""

import ast
from pathlib import Path

class DocstringAdder(ast.NodeTransformer):
    """Add docstrings to test functions."""
    
    def __init__(self):
        self.modified = False
        
    def visit_FunctionDef(self, node):
        if node.name.startswith('test_'):
            # Check if function has docstring
            if not ast.get_docstring(node):
                # Generate docstring based on function name
                test_name = node.name[5:]  # Remove 'test_' prefix
                docstring = f'"""Test {test_name.replace("_", " ")} functionality."""'
                
                # Add docstring as first statement
                docstring_node = ast.Expr(value=ast.Constant(value=docstring.strip('"""')))
                node.body.insert(0, docstring_node)
                self.modified = True
                
        return node

def add_docstrings_to_file(filepath):
    """Add docstrings to test functions in a file."""
    try:
        with open(filepath, 'r') as f:
            content = f.read()
        
        tree = ast.parse(content)
        transformer = DocstringAdder()
        new_tree = transformer.visit(tree)
        
        if transformer.modified:
            # Convert back to source code
            import astor
            new_content = astor.to_source(new_tree)
            
            with open(filepath, 'w') as f:
                f.write(new_content)
            
            return True
    except (IOError, OSError) as e:
        print(f"Error reading/writing file {filepath}: {e}")
    except SyntaxError as e:
        print(f"Syntax error in file {filepath}: {e}")
    except ImportError:
        print("astor module not available - cannot convert AST back to source")
    except Exception as e:
        print(f"Unexpected error processing {filepath}: {e}")
    
    return False

# Sample test files to check
test_files = [
    "blocks/MATH/ARITHMETIC/ADD/ADD_test_.py",
    "blocks/MATH/ARITHMETIC/MULTIPLY/MULTIPLY_test_.py",
    "blocks/DSP/FFT/FFT_test_.py",
    "blocks/DATA/GENERATION/SIMULATIONS/MATRIX/MATRIX_test_.py",
]

for test_file in test_files:
    if Path(test_file).exists():
        print(f"Checking {test_file}...")

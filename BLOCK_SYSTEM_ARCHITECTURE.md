# AtlasVibe Block System Architecture

## Overview

The AtlasVibe block system is a modular architecture that allows users to create visual programming workflows by connecting blocks. Each block represents a computational unit that can process data and pass results to other blocks.

## Block Structure

### Directory Organization

Blocks are organized in a hierarchical directory structure under `/blocks/`:

```
blocks/
├── AI_ML/              # AI and Machine Learning blocks
├── COMPUTER_VISION/    # Computer vision processing blocks
├── CONTROL_FLOW/       # Control flow blocks (loops, conditionals)
├── DATA/               # Data generation, export, and visualization
├── DEBUGGING/          # Debugging and inspection blocks
├── DSP/                # Digital Signal Processing blocks
├── ETL/                # Extract, Transform, Load operations
├── MATH/               # Mathematical operations
├── NUMPY/              # NumPy operations
└── SCIPY/              # SciPy operations
```

### Block Components

Each block consists of the following files:

1. **`BLOCK_NAME.py`** - The main Python implementation
2. **`app.json`** - Example application demonstrating the block's usage
3. **`block_data.json`** - Metadata about the block's documentation
4. **`example.md`** - Markdown documentation with examples
5. **`BLOCK_NAME_test_.py`** - Unit tests (optional)
6. **`assets/`** - Additional resources (optional)

## Block Implementation

### The @flojoy Decorator

Blocks are implemented as Python functions decorated with `@flojoy` (which is currently an alias for `@atlasvibe_node` in the migration from Flojoy to AtlasVibe):

```python
from flojoy import flojoy, OrderedPair, Scalar, Vector

@flojoy
def ADD(
    a: OrderedPair | Scalar | Vector, 
    b: list[OrderedPair | Scalar | Vector]
) -> OrderedPair | Scalar | Vector:
    """Add two or more numeric arrays, matrices, dataframes, or constants element-wise."""
    # Implementation
```

### Decorator Functionality

The `@flojoy` decorator:
- Wraps the function to handle data flow between blocks
- Manages input fetching from previous blocks
- Handles parameter injection from the UI
- Validates outputs
- Manages job results for the execution engine

### Data Containers

Blocks communicate using DataContainer types:
- **OrderedPair**: x,y data pairs
- **Scalar**: Single numeric values
- **Vector**: 1D arrays
- **Matrix**: 2D arrays
- **DataFrame**: Tabular data
- **Image**: Image data
- **Plotly**: Visualization data
- **String**: Text data
- **Boolean**: True/False values

## Block Discovery and Import

### Import System

The `captain/utils/import_blocks.py` module manages block discovery:

1. **Mapping Creation**: Scans the blocks directory and creates a mapping of block names to module paths
2. **Dynamic Import**: Uses Python's `importlib` to dynamically load block modules
3. **Hot Reload**: Supports reloading modules to pick up changes during development

### Block Registration

When a block is imported:
1. The module is loaded and the decorated function is retrieved
2. Any preflight functions are executed
3. Node initialization functions are called if present
4. The block is registered with the execution engine

## Block Metadata

### block_data.json Structure

```json
{
  "docstring": {
    "long_description": "Detailed description...",
    "short_description": "Brief description...",
    "parameters": [
      {
        "name": "param_name",
        "type": "Type",
        "description": "Parameter description"
      }
    ],
    "returns": [
      {
        "name": null,
        "type": "ReturnType",
        "description": "Return value description"
      }
    ]
  }
}
```

### app.json Structure

The `app.json` file contains a complete React Flow graph definition showing how to use the block:
- Node definitions with positions and parameters
- Edge connections between nodes
- Default parameter values
- Example workflows

## Execution Model

### Job Execution Flow

1. **Job Creation**: When a workflow runs, each block execution becomes a "job"
2. **Input Resolution**: The decorator fetches results from previous jobs
3. **Parameter Injection**: UI parameters are formatted and injected
4. **Function Execution**: The block function is called with inputs
5. **Result Storage**: Results are stored in the JobService
6. **Output Propagation**: Results are made available to downstream blocks

### Multiple Inputs

Blocks can accept multiple inputs on a single port:
```python
def BLOCK(a: DataContainer, b: list[DataContainer]) -> DataContainer:
    # 'b' receives multiple connections
```

### Special Features

- **Node Initialization**: Blocks can have init functions for setup
- **Device Connections**: Hardware blocks can inject device connections
- **Stateful Blocks**: Some blocks maintain state between executions
- **Preflight Checks**: Blocks can validate environment before execution

## Creating New Blocks

To create a new block:

1. Create a directory under the appropriate category
2. Implement the Python function with `@flojoy` decorator
3. Create `block_data.json` with documentation
4. Create `app.json` with an example workflow
5. Add unit tests in `BLOCK_NAME_test_.py`
6. Write `example.md` documentation

## Best Practices

1. **Type Hints**: Always use type hints for inputs and outputs
2. **Documentation**: Write comprehensive docstrings
3. **Error Handling**: Handle edge cases gracefully
4. **Testing**: Include unit tests for complex logic
5. **Examples**: Provide clear examples in app.json
6. **Validation**: Validate inputs and outputs appropriately

## Migration Note

The system is currently migrating from "Flojoy" to "AtlasVibe" branding. The `@flojoy` decorator remains for backward compatibility but internally uses the `atlasvibe_node` implementation from the `atlasvibe_sdk` package.
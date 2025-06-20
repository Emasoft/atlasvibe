# AtlasVibe Project Structure

## Overview

AtlasVibe uses a **folder-based project structure** where each project is self-contained with its own custom blocks and workflow definition.

## Directory Structure

```
project_name/                              # Project folder
├── project_name.atlasvibe                # Project file (JSON format)
└── atlasvibe_blocks/                     # Custom blocks folder
    ├── __init__.py                       # Python package marker
    ├── BLOCK_NAME_1/                     # Custom block instance
    │   ├── __init__.py
    │   ├── BLOCK_NAME_1.py              # Block implementation
    │   ├── block_data.json              # Block metadata
    │   ├── app.json                     # Example usage
    │   ├── example.md                   # Documentation
    │   └── requirements.txt             # Optional dependencies
    └── BLOCK_NAME_2/                     # Another custom block
        └── ...
```

## Key Concepts

### Blueprint Blocks vs Custom Blocks

1. **Blueprint Blocks** (Global)
   - Located in `/blocks/` at AtlasVibe root
   - Serve as templates in the global palette
   - Never directly used in workflows
   - Shared across all projects

2. **Custom Blocks** (Project-specific)
   - Located in `project_folder/atlasvibe_blocks/`
   - Instances/copies of blueprint blocks
   - Can be edited without affecting blueprints
   - Specific to each project

### Workflow

1. **Creating a Block Instance**
   - User drags blueprint from palette to workflow
   - System creates a copy in `project_folder/atlasvibe_blocks/`
   - Names it with suffix (e.g., `ADD_1`, `ADD_2`)
   - Block is now independent of blueprint

2. **Editing Custom Blocks**
   - Changes only affect that specific instance
   - Other instances and blueprints remain unchanged
   - Each block has its own virtual environment

3. **Saving as Blueprint**
   - Custom blocks can be saved back as blueprints
   - Creates/updates global blueprint for reuse

## Project File Format

The `.atlasvibe` file contains:

```json
{
  "version": "2.0.0",
  "name": "My Project",
  "rfInstance": {
    "nodes": [
      {
        "id": "ADD-uuid-here",
        "data": {
          "func": "ADD_1",           // References custom block
          "isCustom": true,          // Marks as custom block
          "path": "atlasvibe_blocks/ADD_1/ADD_1.py",
          // ... other properties
        }
      }
    ],
    "edges": [...]
  }
}
```

## Migration from Old Format

Old projects used blueprint references directly. The new format requires:
1. Each block to be copied to `atlasvibe_blocks/`
2. References updated to point to custom blocks
3. `isCustom: true` flag added

Use the migration script: `python scripts/migrate_sample_projects.py`

## Loading Projects

When a project is loaded:
1. System validates project structure
2. Creates `atlasvibe_blocks/` if missing
3. Loads custom blocks from project directory
4. Falls back to blueprints if custom blocks missing

## Benefits

- **Isolation**: Projects are self-contained
- **Portability**: Easy to share/move projects
- **Version Control**: Each project tracks its own blocks
- **Customization**: Edit blocks without affecting other projects
- **Dependency Management**: Each block has its own virtual environment

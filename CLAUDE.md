# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AtlasVibe is an open-source visual programming IDE for Python (currently in active development). It's a fork of Flojoy Studio, reimagined as a general-purpose visual IDE where users construct Python applications by connecting visual nodes. The long-term vision includes AI-powered nodes that can self-generate or modify code based on user intent.

## Development Commands

### Environment Setup
```bash
# Python environment (using uv)
uv venv
source .venv/bin/activate  # Linux/macOS
uv sync --all-extras       # Install all dependencies

# Node.js dependencies
pnpm install
```

### Running the Application
```bash
# Full stack (frontend + backend)
pnpm run start-project

# Backend only
uv run python3 main.py
# or debug mode:
pnpm run backend:debug

# Frontend only
pnpm run dev
```

### Testing
```bash
# All tests
bash runtests.sh

# Python tests only
uv run pytest .

# Run specific test file
uv run pytest path/to/test_file.py

# E2E tests
pnpm run e2e
```

### Code Quality
```bash
# Python formatting
just format  # or: uv run ruff format .

# Python linting
just lint    # or: uv run ruff check .

# TypeScript/JavaScript
pnpm run lint    # ESLint
pnpm run format  # Prettier
```

### Building
```bash
# Frontend build
pnpm run build

# Electron packages
pnpm run electron-package         # All platforms
pnpm run electron-package:windows  # Windows only
pnpm run electron-package:mac      # macOS only
pnpm run electron-package:linux    # Linux only
```

### Block Management
```bash
# Sync Python blocks
just sync

# Add new blocks
just add <path>

# Initialize docs and blocks
just init
```

## Architecture Overview

### Project Structure
- **Frontend**: Electron + React + TypeScript application
  - `/src/renderer/` - React components and application logic
  - `/src/main/` - Electron main process
  - Uses ReactFlow for visual programming interface
  - Plotly for data visualization
  - State management with Zustand stores

- **Backend**: Python FastAPI server
  - `/captain/` - Main backend application
    - `/routes/` - API endpoints
    - `/services/` - Business logic
    - `/models/` - Data models
  - `/main.py` - Entry point
  - Uses Prefect for workflow management

- **Block System**: Modular visual programming nodes
  - `/blocks/` - Blueprint blocks organized by category
  - Each block is a Python function decorated with `@flojoy`
  - Blocks communicate via DataContainer objects
  - Dynamic discovery and import system

- **SDKs**:
  - `/pkgs/atlasvibe_sdk/` - Core SDK for block development
  - `/pkgs/flojoy/` - Legacy SDK (being migrated)

### Key Architecture Concepts

#### Block System
Blocks are the fundamental units in AtlasVibe. Each block:
- Is a Python function with `@flojoy` decorator
- Accepts DataContainer objects as inputs
- Returns DataContainer objects as outputs
- Has metadata files (app.json, block_data.json) for UI configuration
- Can have custom virtual environments for dependencies

Example block structure:
```
blocks/CATEGORY/SUBCATEGORY/BLOCK_NAME/
├── BLOCK_NAME.py          # Main implementation
├── app.json               # UI configuration
├── block_data.json        # Parameter definitions
├── example.md             # Documentation
└── requirements.txt       # Optional dependencies
```

#### Workflow Execution
1. User creates visual flow in ReactFlow canvas
2. Frontend sends graph topology to backend
3. Backend uses Prefect to execute blocks in correct order
4. Results are streamed back via WebSocket
5. Frontend displays results using appropriate visualizations

#### Communication Flow
- Frontend ↔ Backend: REST API + WebSocket
- Backend executes blocks using Python multiprocessing
- Blocks communicate through serialized DataContainer objects
- Results cached using joblib for performance

### Development Workflow

When implementing new features:
1. For UI changes: Start in `/src/renderer/`
2. For block functionality: Work in `/blocks/` or create custom blocks
3. For API changes: Update both `/captain/routes/` and `/captain/types/`
4. For execution logic: Modify `/captain/services/` and worker processes

### Important Implementation Details

- **Block Discovery**: `captain/utils/import_blocks.py` dynamically imports all blocks at startup
- **Manifest Generation**: Block metadata is auto-generated from Python docstrings and decorators
- **Type System**: Uses Pydantic for API validation and TypeScript interfaces for frontend
- **State Management**: Zustand stores in `/src/renderer/stores/` manage application state
- **WebSocket**: Real-time communication for workflow execution status and results

### Current Development Focus

The project is being refactored from Flojoy Studio to AtlasVibe with these priorities:
1. Implementing project-centric block management (blocks per project, not global)
2. Enabling in-IDE block code editing
3. Transitioning from hardware test sequencer to general-purpose visual programming
4. Future: AI agent capabilities for code generation within blocks

See DEVELOPMENT_PLAN.md for detailed roadmap and implementation strategy.

## Mass Find Replace (MFR) Tool

The codebase includes a powerful mass find/replace tool (`mass_find_replace.py`) for safely renaming symbols across the entire project. This tool was specifically designed for the Flojoy → AtlasVibe migration.

### Key Features
- **Safe renaming**: Handles files, folders, and content with proper ordering (folders shallow→deep, then files, then content)
- **Collision detection**: Detects and logs naming collisions (both exact and case-insensitive)
- **Binary file handling**: Detects matches in binary files but doesn't modify them
- **Resume capability**: Can resume interrupted operations
- **Dry-run mode**: Preview changes before execution
- **Transaction logging**: All changes are logged with rollback information

### Collision Handling
When renaming files or folders, the tool performs case-insensitive collision detection:
- On case-insensitive filesystems (like macOS), `File.txt` and `file.txt` are the same
- Collisions are logged to `collisions_errors.log` with full details
- Colliding renames are skipped to prevent data loss
- Manual intervention is required to resolve collisions

### Usage Example
```bash
# Dry run to preview changes
uv run python mass_find_replace.py . --dry-run

# Execute with default mapping (replacement_mapping.json)
uv run python mass_find_replace.py .

# Resume a previous run
uv run python mass_find_replace.py . --resume
```

### Important Files
- `replacement_mapping.json`: Defines string replacements
- `planned_transactions.json`: Transaction log
- `binary_files_matches.log`: Binary file matches (informational)
- `collisions_errors.log`: Naming collision details
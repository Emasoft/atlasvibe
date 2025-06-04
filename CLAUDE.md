# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## General Development Guidelines and Rules
- *CRITICAL*: when reading the lines of the source files, do not read just few lines like you usually do. Instead always read all the lines of the file (until you reach the limit of available context memory). No matter what is the situation, searching or editing a file, ALWAYS OBEY TO THIS RULE!!!.
- be extremely meticulous and accurate. always check twice any line of code for errors before output the code.
- never output code that is abridged or with parts replaced by placeholder comments like `# ... rest of the code ...`, `# ... rest of the function as before ...`, `# ... rest of the code remains the same ...`, or similar. You are not chatting. The code you output is going to be saved and linted, so omitting parts of it will cause errors and broken files.
- Be conservative. only change the code that it is strictly necessary to change to implement a feature or fix an issue. Do not change anything else. You must report the user if there is a way to improve certain parts of the code, but do not attempt to do it unless the user explicitly asks you to. 
- when fixing the code, if you find that there are multiple possible solutions, do not start immediately but first present the user all the options and ask him to choose the one to try. For trivial bugs you don't need to, of course.
- never remove unused code or variables unless they are wrong, since the program is a WIP and those unused parts are likely going to be developed and used in the future. The only exception is if the user explicitly tells you to do it.
- Don't worry about functions imported from external modules, since those dependencies cannot be always included in the chat for your context limit. Do not remove them or implement them just because you can''t find the module or source file they are imported from. You just assume that the imported modules and imported functions work as expected. If you need to change them, ask the user to include them in the chat.
- spend a long time thinking deeply to understand completely the code flow and inner working of the program before writing any code or making any change. 
- if the user asks you to implement a feature or to make a change, always check the source code to ensure that the feature was not already implemented before or it is implemented in another form. Never start a task without checking if that task was already implemented or done somewhere in the codebase.
- if you must write a function, always check if there are already similar functions that can be extended or parametrized to do what new function need to do. Avoid writing duplicated or similar code by reusing the same flexible helper functions where is possible.
- keep the source files as small as possible. If you need to create new functions or classes, prefer creating them in new modules in new files and import them instead of putting them in the same source file that will use them. Small reusable modules are always preferable to big functions and spaghetti code.
- try to edit only one source file at time. Keeping only one file at time in the context memory will be optimal. When you need to edit another file, ask the user to remove from the chat context the previous one and to add the new one. You can aleays use the repo map to get an idea of the content of the other files.
- always use type annotations
- always preserve comments and add them when writing new code.
- always write the docstrings of all functions and improve the existing ones. 
- only use google style docstrings, but do not use markdown. 
- never use markdown in comments. 
- always use a **Test-Driven Development (TDD)** methodology (write tests first, the implementation later) when implementing new features or change the existing ones. But first check that the existing tests are written correctly.
- always plan in advance your actions, and break down your plan into very small tasks. Save a file named `DEVELOPMENT_PLAN.md` and write all tasks inside it. Update it with the status of each tasks after any changes.
- Commit often. Never mention Claude as the author of the commits.
- **Auto-Lint after changes**: Always run a linter (like ruff or shellcheck) after any changes to the files.
- always add the following shebang at the beginning of each python file: 

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
```
- always add a short changelog before the imports in of the source code to document all the changes you made to it.

```python
# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# <your changelog here…>
# 
```

## Development Commands

### Environment Setup
```bash
# Python environment (using uv)
uv venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows
uv sync --all-extras       # Install all dependencies

# Node.js dependencies
pnpm install
```

### Running the Application
```bash
# Full stack (frontend + backend)
pnpm run start-project            # macOS/Linux
pnpm run start-project:win        # Windows
pnpm run start-project:debug      # Debug mode

# Backend only
uv run python3 main.py            # or: python main.py on Windows
uv run python3 main.py --log-level debug  # Debug mode

# Frontend only
pnpm run dev
```

### Testing
```bash
# All tests
bash runtests.sh

# Python tests only
uv run pytest .
uv run pytest path/to/test_file.py         # Specific file
uv run pytest path/to/test_file.py::test_function  # Specific test
uv run pytest -k "test_name"               # By test name pattern
uv run pytest -m "not slow"                # Skip slow tests

# Frontend E2E tests
pnpm run e2e
npx playwright test                        # Alternative
npx playwright test --ui                   # With UI mode
```

### Code Quality
```bash
# Python formatting and linting
just format              # or: uv run ruff format .
just lint                # or: uv run ruff check .
uv run ruff check --fix  # Auto-fix linting issues

# TypeScript/JavaScript
pnpm run lint            # ESLint
pnpm run format          # Prettier
pnpm run check           # Check formatting without fixing
```

### Building and Packaging
```bash
# Frontend build
pnpm run build

# Electron packages
pnpm run electron-package          # All platforms
pnpm run electron-package:windows   # Windows only
pnpm run electron-package:mac       # macOS only
pnpm run electron-package:linux     # Linux only
```

### Block Management
```bash
# Sync Python blocks (regenerate manifests)
just sync                # or: uv run python3 fjblock.py sync

# Add new blocks from a directory
just add <path>          # or: uv run python3 fjblock.py add <path>

# Initialize docs and blocks
just init
```

## Architecture Overview

AtlasVibe is a visual programming IDE for Python, consisting of three main components:

### 1. Frontend (Electron + React + TypeScript)
- **Entry Point**: `/src/main/index.ts` (Electron main process)
- **UI Components**: `/src/renderer/` (React application)
  - `/components/` - Reusable UI components
  - `/routes/` - Page-level components (flow chart, control panel, etc.)
  - `/stores/` - Zustand state management
  - `/hooks/` - Custom React hooks
  - `/lib/` - Utility functions and API clients
- **Key Technologies**:
  - ReactFlow for visual programming canvas
  - Plotly for data visualization
  - TailwindCSS for styling
  - Zustand for state management

### 2. Backend (Python FastAPI Server)
- **Entry Point**: `/main.py`
- **Application Code**: `/captain/`
  - `/routes/` - API endpoints (blocks, flowchart, devices, etc.)
  - `/services/` - Business logic layer
  - `/models/` - Pydantic models for data validation
  - `/types/` - TypeScript-compatible type definitions
  - `/utils/` - Helper functions and utilities
- **Key Technologies**:
  - FastAPI for REST API
  - Prefect for workflow orchestration
  - WebSocket for real-time communication
  - Pydantic for data validation

### 3. Block System
- **Blueprint Blocks**: `/blocks/` - Organized by category (AI_ML, DSP, MATH, etc.)
- **Block Structure**:
  ```
  blocks/CATEGORY/SUBCATEGORY/BLOCK_NAME/
  ├── BLOCK_NAME.py          # Main implementation with @atlasvibe decorator
  ├── app.json               # UI metadata (position, color, etc.)
  ├── block_data.json        # Parameter definitions
  ├── example.md             # Documentation
  ├── requirements.txt       # Optional dependencies
  └── *_test_.py             # Unit tests
  ```
- **SDKs**:
  - `/pkgs/atlasvibe_sdk/` - Core SDK for block development
  - `/pkgs/atlasvibe/` - Legacy SDK (contains DataContainer, node decorators)

## Key Architectural Patterns

### Block Execution Flow
1. User creates visual flow in ReactFlow canvas
2. Frontend sends topology to backend via `/blocks/run` API
3. Backend creates Prefect flow from topology
4. Worker processes execute blocks in dependency order
5. Results stream back via WebSocket to frontend
6. Frontend renders results using appropriate visualizations

### Data Flow Between Blocks
- Blocks communicate via `DataContainer` objects
- DataContainer wraps various data types (scalar, vector, matrix, dataframe, etc.)
- Serialization handled automatically between processes
- Results cached using joblib for performance

### Dynamic Block Discovery
- On startup, `captain/utils/import_blocks.py` scans `/blocks/` directory
- Manifest generator (`captain/utils/manifest/`) extracts metadata from Python decorators
- Block registry maintained in memory for fast lookup
- Frontend fetches available blocks via `/blocks` API

### WebSocket Communication Protocol
- Connection established at `/ws`
- Message types: WORKER_STARTED, BLOCK_STARTED, BLOCK_FINISHED, JOB_STARTED, etc.
- Enables real-time progress tracking and result streaming

## Important Development Patterns

### Adding New API Endpoints
1. Define Pydantic models in `/captain/models/`
2. Create TypeScript types in `/captain/types/`
3. Implement endpoint in `/captain/routes/`
4. Update frontend API client in `/src/lib/api.ts`

### Creating New Blocks
1. Create directory structure under appropriate category in `/blocks/`
2. Implement block function with `@atlasvibe` decorator
3. Define parameters in docstring and decorator
4. Run `just sync` to regenerate manifests
5. Block automatically appears in UI

### State Management
- Zustand stores in `/src/renderer/stores/`:
  - `app.ts` - Application-wide state
  - `flowchart.ts` - Visual flow editor state
  - `socket.ts` - WebSocket connection state
  - `project.ts` - Project management state
- Follow pattern of actions as methods, state as properties

### Testing Patterns
- Python blocks: Place `*_test_.py` files alongside block implementation
- Backend API: Tests in `/captain/tests/`
- Frontend components: Tests in `/tests/`
- E2E tests: Playwright tests in `/playwright-test/`

## Current Development Focus

The project is transitioning from hardware test sequencer to general-purpose visual IDE:
1. **Project-Centric Blocks**: Moving from global blocks to per-project custom blocks
2. **In-IDE Editing**: Enabling code editing within the application
3. **AI Agent Capabilities**: Future goal for self-modifying blocks

See DEVELOPMENT_PLAN.md for detailed roadmap.


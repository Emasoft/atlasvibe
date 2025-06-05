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

----------------------------------------

TITLE: Creating Virtual Environment with Specific Python Version using uv (Console)
DESCRIPTION: Creates a virtual environment using a specific Python version (e.g., 3.11) with the `uv` tool. Requires the requested Python version to be available or downloadable by uv.
SOURCE: https://github.com/astral-sh/uv/blob/main/docs/pip/environments.md#_snippet_2

LANGUAGE: console
CODE:
```
$ uv venv --python 3.11
```

----------------------------------------

TITLE: Creating a Virtual Environment with uv
DESCRIPTION: This command creates a new virtual environment in the current directory using `uv venv`. It automatically detects the appropriate Python version and provides instructions for activating the environment.
SOURCE: https://github.com/astral-sh/uv/blob/main/README.md#_snippet_14

LANGUAGE: console
CODE:
```
$ uv venv
Using Python 3.12.3
Creating virtual environment at: .venv
Activate with: source .venv/bin/activate

------------------------------------------

## Managed and system Python installations
Since it is common for a system to have an existing Python installation, uv supports discovering Python versions. However, uv also supports installing Python versions itself. To distinguish between these two types of Python installations, uv refers to Python versions it installs as managed Python installations and all other Python installations as system Python installations.

Note
uv does not distinguish between Python versions installed by the operating system vs those installed and managed by other tools. For example, if a Python installation is managed with pyenv, it would still be considered a system Python version in uv.


## Requesting a version
A specific Python version can be requested with the --python flag in most uv commands. For example, when creating a virtual environment:


$ uv venv --python 3.11.6

uv will ensure that Python 3.11.6 is available — downloading and installing it if necessary — then create the virtual environment with it.
The following Python version request formats are supported:

	•	<version> (e.g., 3, 3.12, 3.12.3)
	•	<version-specifier> (e.g., >=3.12,<3.13)
	•	<implementation> (e.g., cpython or cp)
	•	<implementation>@<version> (e.g., cpython@3.12)
	•	<implementation><version> (e.g., cpython3.12 or cp312)
	•	<implementation><version-specifier> (e.g., cpython>=3.12,<3.13)
	•	<implementation>-<version>-<os>-<arch>-<libc> (e.g., cpython-3.12.3-macos-aarch64-none)
	
Additionally, a specific system Python interpreter can be requested with:

	•	<executable-path> (e.g., /opt/homebrew/bin/python3)
	•	<executable-name> (e.g., mypython3)
	•	<install-dir> (e.g., /some/environment/)
	
By default, uv will automatically download Python versions if they cannot be found on the system. This behavior can be disabled with the python-downloads option.


## Python version files
The .python-version file can be used to create a default Python version request. uv searches for a .python-version file in the working directory and each of its parents. If none is found, uv will check the user-level configuration directory. Any of the request formats described above can be used, though use of a version number is recommended for interoperability with other tools.
A .python-version file can be created in the current directory with the uv python pin command:

## Change to use a specific Python version in the current directory

```
$ uv python pin 3.11

Pinned `.python-version` to `3.11`
```

A global .python-version file can be created in the user configuration directory with the uv python pin --global command. (not reccomended)

## Discovery of .python-version files can be disabled with --no-config.
uv will not search for .python-version files beyond project or workspace boundaries (with the exception of the user configuration directory).

## Installing a Python version
uv bundles a list of downloadable CPython and PyPy distributions for macOS, Linux, and Windows.

Tip
By default, Python versions are automatically downloaded as needed without using uv python install.

To install a Python version at a specific version:


$ uv python install 3.12.3

To install the latest patch version:


$ uv python install 3.12

To install a version that satisfies constraints:


$ uv python install '>=3.8,<3.10'

To install multiple versions:


$ uv python install 3.9 3.10 3.11

To install a specific implementation:


$ uv python install pypy

All of the Python version request formats are supported except those that are used for requesting local interpreters such as a file path.
By default uv python install will verify that a managed Python version is installed or install the latest version. If a .python-version file is present, uv will install the Python version listed in the file. A project that requires multiple Python versions may define a .python-versions file. If present, uv will install all of the Python versions listed in the file.

Important
The available Python versions are frozen for each uv release. To install new Python versions, you may need upgrade uv.

## Installing Python executables

To install Python executables into your PATH, provide the --preview option:


$ uv python install 3.12 --preview
This will install a Python executable for the requested version into ~/.local/bin, e.g., as python3.12.

Tip
If ~/.local/bin is not in your PATH, you can add it with uv tool update-shell.

To install python and python3 executables, include the --default option:


$ uv python install 3.12 --default --preview

When installing Python executables, uv will only overwrite an existing executable if it is managed by uv — e.g., if ~/.local/bin/python3.12 exists already uv will not overwrite it without the --force flag.
uv will update executables that it manages. However, it will prefer the latest patch version of each Python minor version by default. For example:


$ uv python install 3.12.7 --preview  # Adds `python3.12` to `~/.local/bin`

$ uv python install 3.12.6 --preview  # Does not update `python3.12`

$ uv python install 3.12.8 --preview  # Updates `python3.12` to point to 3.12.8

## Project Python versions
uv will respect Python requirements defined in requires-python in the pyproject.toml file during project command invocations. The first Python version that is compatible with the requirement will be used, unless a version is otherwise requested, e.g., via a .python-version file or the --python flag.

## Viewing available Python versions
To list installed and available Python versions:


$ uv python list

To filter the Python versions, provide a request, e.g., to show all Python 3.13 interpreters:


$ uv python list 3.13

Or, to show all PyPy interpreters:


$ uv python list pypy

By default, downloads for other platforms and old patch versions are hidden.
To view all versions:


$ uv python list --all-versions

To view Python versions for other platforms:


$ uv python list --all-platforms

To exclude downloads and only show installed Python versions:


$ uv python list --only-installed

See the uv python list reference for more details.

## Finding a Python executable
To find a Python executable, use the uv python find command:

$ uv python find

By default, this will display the path to the first available Python executable. See the discovery rules for details about how executables are discovered.

This interface also supports many request formats, e.g., to find a Python executable that has a version of 3.11 or newer:

$ uv python find '>=3.11'

By default, uv python find will include Python versions from virtual environments. If a .venv directory is found in the working directory or any of the parent directories or the VIRTUAL_ENV environment variable is set, it will take precedence over any Python executables on the PATH.
To ignore virtual environments, use the --system flag:

$ uv python find --system

But it is not reccomended.

## Discovery of Python versions
When searching for a Python version, the following locations are checked:
	•	Managed Python installations in the UV_PYTHON_INSTALL_DIR.
	•	A Python interpreter on the PATH as python, python3, or python3.x on macOS and Linux, or python.exe on Windows.
	•	On Windows, the Python interpreters in the Windows registry and Microsoft Store Python interpreters (see py --list-paths) that match the requested version.

In some cases, uv allows using a Python version from a virtual environment. In this case, the virtual environment's interpreter will be checked for compatibility with the request before searching for an installation as described above. See the pip-compatible virtual environment discovery documentation for details.
When performing discovery, non-executable files will be ignored. Each discovered executable is queried for metadata to ensure it meets the requested Python version. If the query fails, the executable will be skipped. If the executable satisfies the request, it is used without inspecting additional executables.
When searching for a managed Python version, uv will prefer newer versions first. When searching for a system Python version, uv will use the first compatible version — not the newest version.
If a Python version cannot be found on the system, uv will check for a compatible managed Python version download.

## EXAMPLE OF INSTALLING A VERSION OF PYTHON AND CHANGING IT LATER WITH PIN:

## Install multiple Python versions:

```
$ uv python install 3.10 3.11 3.12

Searching for Python versions matching: Python 3.10

Searching for Python versions matching: Python 3.11

Searching for Python versions matching: Python 3.12

Installed 3 versions in 3.42s

 + cpython-3.10.14-macos-aarch64-none

 + cpython-3.11.9-macos-aarch64-none

 + cpython-3.12.4-macos-aarch64-none
 ```
 
## Download Python versions as needed:

```
$ uv venv --python 3.12.0

Using CPython 3.12.0

Creating virtual environment at: .venv

Activate with: source .venv/bin/activate


$ uv run --python pypy@3.8 -- python

Python 3.8.16 (a9dbdca6fc3286b0addd2240f11d97d8e8de187a, Dec 29 2022, 11:45:30)

[PyPy 7.3.11 with GCC Apple LLVM 13.1.6 (clang-1316.0.21.2.5)] on darwin

Type "help", "copyright", "credits" or "license" for more information.
```

## Change to use a specific Python version in the current directory:

```
$ uv python pin 3.11

Pinned `.python-version` to `3.11`
```

------------------------------------------

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

# Build Python package (includes Electron app)
./install.sh              # Full installation from source
uv run python -m build    # Build wheel only

# Install package
pip install dist/*.whl    # Install built wheel
pip install -e .         # Development install
```

### Running AtlasVibe
```bash
# After installation via pip
atlasvibe                    # Run full application
atlasvibe server             # Run backend server only
atlasvibe ui                 # Run UI only
atlasvibe ui --dev          # Run UI in development mode
atlasvibe init my-project    # Create new project

# Development mode (without installation)
uv run python main.py        # Run backend
pnpm run dev                 # Run frontend (separate terminal)
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

## Package Structure (NEW)

AtlasVibe is now distributed as a standard Python package that includes both backend and frontend:

### No More ASAR Packaging
- Electron app is distributed unpacked (asar: false)
- Simplifies file access and debugging
- No more path resolution issues with process.resourcesPath
- All files are directly accessible in the installed package

### Unified Distribution
- Single `pip install atlasvibe` installs everything
- No need for platform-specific Electron builds
- Python backend and Electron frontend in same package
- Simplified deployment and version management

### Installation Methods
1. **From Source**: `./install.sh` - builds and installs complete package
2. **From PyPI**: `pip install atlasvibe` (when published)
3. **Development**: `pip install -e .` for editable install

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

## Testing Best Practices

### Avoid Unnecessary Mocks
- **CRITICAL**: Mocks should be used ONLY when it is impossible to test otherwise (e.g., external services, hardware dependencies)
- Mocks can mask real functionality and hide bugs - prefer real integration tests
- When testing file operations, use real temporary directories and files instead of mocking the filesystem
- When testing API endpoints, use TestClient with the actual FastAPI app instead of mocking HTTP calls
- For database operations, use a test database or in-memory database instead of mocking

### Building and Running Tests
- **Before running Playwright tests**: The application MUST be built first
  ```bash
  pnpm run build
  pnpm run electron-package:mac  # or :windows/:linux
  ```
- Install all dependencies before testing:
  ```bash
  pnpm install  # For Node.js dependencies
  uv sync --all-extras  # For Python dependencies
  ```
- For Python packages in development, install them:
  ```bash
  cd pkgs/atlasvibe && uv pip install -e .
  ```

### Test Organization
- Unit tests: Test individual functions with minimal dependencies
- Integration tests: Test complete workflows with real components
- E2E tests: Test the full application behavior from user perspective
- Always prefer integration tests over unit tests with heavy mocking

### Example of Good Testing Practice
```python
# GOOD: Real file operations
def test_update_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "test.txt"
        file_path.write_text("original")
        
        # Test actual file update
        update_file(file_path, "new content")
        assert file_path.read_text() == "new content"

# BAD: Mocking file operations
def test_update_file_with_mock():
    mock_path = Mock()
    mock_path.read_text.return_value = "original"
    
    # This doesn't test real file behavior
    update_file(mock_path, "new content")
    mock_path.write_text.assert_called_with("new content")
```

### Running Tests in CI/CD
- Set up environment variables properly
- Ensure all dependencies are installed
- Build the application before E2E tests
- Use headless mode for Playwright tests in CI


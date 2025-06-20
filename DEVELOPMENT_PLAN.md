# atlasvibe Development Plan

## Project Overview

Transform the forked project from a lab-focused visual programming IDE ("Flojoy Studio") into "atlasvibe," a general-purpose visual programming IDE for Python. A key feature will be an Agent node flow approach, where each node (block/agent) can eventually generate its own Python code.

## Phase 1: Rebranding and Initial Cleanup ✅ COMPLETED

This phase focuses on changing the project's identity from "Atlasvibe Studio" to "atlasvibe" and updating all relevant information.

**Task 1.1: Project Name and Identity**
*   **Action:** Globally replace the remaining occurrences of "Flojoy  Studio", "Flojoy", "flojoy-ai" (where appropriate, distinguishing from the `flojoy` Python library if it's reused) with "atlasvibe" and "Emasoft".
*   **Scope:** Update codebase comments, UI text, internal identifiers, assets names, documentation, marketing materials (if any).
*   **Details:**
    *   Update window titles, application names.
    *   Plan for new logo and branding assets (initial step: remove old logo).

**Task 1.2: URL and Repository Updates**
*   **Action:** Update all URLs to point to the new repository: `https://github.com/Emasoft/atlasvibe`.
*   **Scope:** `README.md`, links within the application (e.g., "Help", "About"), CI configuration files, any other documentation.

**Task 1.3: Author, Copyright, and Acknowledgments**
*   **Action:**
    *   Change primary author and copyright holder to "Emasoft".
    *   Update `LICENSE` file (already done) or add a `NOTICE` file if more detailed acknowledgments are needed beyond README/About.
    *   In `README.md` and any "About" sections, clearly state that atlasvibe is forked from the open-source Atlasvibe Studio project.
    *   Acknowledge the original developers/project for their foundational work. Ensure compliance with the original MIT license.
*   **Example Acknowledgment Text (to be refined):**
    > "atlasvibe is a derivative of Flojoy Studio, an open-source project originally developed by the Flojoy team. We extend our gratitude for their significant contributions and for making their work available under the MIT license. Atlasvibe aims to build upon this foundation for new purposes, and all original licensing terms are respected."

**Task 1.4: README.md Update**
*   **Action:** Perform a thorough rewrite of `README.md`. (Initial version already created).
*   **Details:**
    *   Reflect the new project name "atlasvibe" and its goals.
    *   Clearly state that the project is a **work in progress and not currently usable.**
    *   Remove/update screenshots, features list, and architecture diagrams that are specific to Flojoy Studio's original purpose.
    *   Update or remove the "Quickstart" section.
    *   Adjust CI badges once new CI/CD is set up for `Emasoft/atlasvibe`. Initially, remove old badges.

**Task 1.5: UI Text and Asset Review**
*   **Action:** Systematically review all user-facing text.
*   **Scope:** Buttons, labels, tooltips, menu items, "About" dialogs, "Help" sections, links.
*   **Details:** Ensure all references to "Atlasvibe", its specific features (e.g., "test sequencer for hardware validation" unless retained), or personnel are updated or removed. Remove the old logo from the UI.

## Phase 2: Core Block System Transformation (IN PROGRESS)

This phase redefines how blocks are created, managed, and used within a project.

**Current State Analysis (December 2024):**
- Projects are saved as `.atlasvibe` JSON files containing nodes, edges, and text nodes
- Blocks are globally loaded from `/blocks/` directory at startup
- The frontend already has placeholder code for custom blocks (see `useAddBlock` in `project.ts`)
- The IPC handler for `create-custom-block` is declared but not implemented
- Block manifests are generated from Python docstrings and decorators

**Task 2.1: Project-Centric Structure** ✅ COMPLETED
*   **Action:** Define and implement a new project structure where each atlasvibe project is self-contained in its own directory.
*   **Details:**
    *   A project directory will contain the main flow/graph file and a subdirectory for its custom blocks (e.g., `MyProject/atlasvibe_blocks/`).
    *   The concept of globally importing a "custom blocks folder" will be removed. The project's block directory *is* the custom blocks source for that project.
*   **Implementation:**
    *   Created `captain/utils/project_structure.py` module with utilities for managing project directories
    *   Projects now have an `atlasvibe_blocks/` directory for custom blocks
    *   Added validation and initialization functions for project structures

**Task 2.2: Block Blueprints**
*   **Action:** Treat existing blocks (e.g., those in the current `./blocks/` directory) as "blueprints."
*   **Details:**
    *   These blueprints will be listed in the UI for users to select from when adding a new node.
    *   Blueprints themselves are not directly part of a user's project graph but are templates.

**Task 2.3: Custom Block Creation on-the-fly** ✅ PARTIAL IMPLEMENTATION
*   **Action:** Implement the new workflow for adding blocks to a project.
*   **Details:**
    *   When a user adds a block (e.g., drags a blueprint to the canvas):
        1.  Prompt the user for a new, unique name for this specific instance (e.g., "MyCustomMatrixViewer").
        2.  Duplicate the chosen blueprint's entire folder (e.g., `MATRIX_VIEW/`) into the current project's `atlasvibe_blocks/` directory, renaming the folder to the user-provided name.
        3.  Rename the main Python file inside this new folder (e.g., `MATRIX_VIEW.py` to `MyCustomMatrixViewer.py`).
        4.  **Crucially, update the `@atlasvibe` decorated function name inside the new Python file to match the new filename/block name.** This is essential for the system to recognize it.
        5.  Update metadata files (`app.json`, `block_data.json`) within the new custom block's folder to reflect its new name and identity.
    *   This new, duplicated block is now a "custom block" specific to the current project.
*   **Implementation:**
    *   Backend API endpoint `/blocks/create-custom/` implemented
    *   IPC handler added for `create-custom-block` event
    *   Frontend `useAddBlock` hook already prompts for name and calls the API
    *   Function renaming and metadata updates implemented in `project_structure.py`
    *   **Still needed:** Update the block discovery/loading to include project-specific blocks

**Task 2.4: Project-Scoped Block Loading and Management** ✅ COMPLETED
*   **Action:** Modify the application to discover and load blocks primarily from the active project's `atlasvibe_blocks/` directory.
*   **Details:**
    *   The application should also be able to access the "blueprint" blocks for creation purposes but not execute them directly in a flow.
    *   The UI for selecting blocks should clearly distinguish between adding a new custom block (from a blueprint) and potentially reusing an existing custom block within the same project.
*   **Implementation:**
    *   Created `ProjectBlocksLoader` class to manage both blueprint and project blocks
    *   Modified import system to prioritize project blocks over blueprints
    *   Updated manifest generation to include "Project Blocks" section
    *   Backend now receives project_path for block loading during execution
    *   Project blocks are dynamically loaded from `atlasvibe_blocks/` directory

**Task 2.5: In-IDE Block Code Editing and Synchronization** ✅ COMPLETED
*   **Action:** Enable users to edit the Python code of their custom blocks directly within the atlasvibe IDE.
*   **Details:**
    *   Each node representing a custom block should have an "Edit Code" option.
    *   When code is saved:
        1.  The corresponding Python file in the project's `atlasvibe_blocks/` directory is updated.
        2.  A process to regenerate metadata (`app.json`, `block_data.json`) for that specific custom block is triggered. This might involve re-parsing the Python file for the `@atlasvibe` decorator and its parameters.
*   **Implementation (using TDD methodology):**
    *   Created comprehensive tests for both backend and frontend functionality
    *   Backend API endpoint `/blocks/update-code/` implemented with:
        - Validation to ensure only custom blocks can be edited
        - Automatic backup of original content
        - Manifest/metadata regeneration after code update
        - Rollback mechanism on failure
    *   Frontend EditorView component enhanced with:
        - Detection of custom blocks (shows "Custom Block" indicator)
        - Integration with backend API for metadata regeneration
        - Success/error notifications
        - Automatic manifest refresh after save
    *   Context menu "Edit Python Code" option already opens the editor window
    *   Full synchronization between code editor and block metadata
*   **Python Environment Management:**
    *   Migrated from Poetry to uv for faster, more reliable dependency management
    *   Created deployment scripts that properly configure Python 3.11 environment
    *   Fixed module import issues with proper package installation
    *   Updated all Python-related commands in TypeScript to use uv instead of Poetry
    *   Created comprehensive build and test scripts:
        - `build-and-test.sh` - Complete build and test pipeline with uv
        - `run-tests-with-uv.sh` - Run Playwright tests with backend server
        - `run-server-with-uv.sh` - Run server directly without Electron
        - `run-with-uv.sh` - Run either server or app with proper environment

**Task 2.6: Data Persistence and Project Files** ✅ COMPLETED
*   **Action:** Define how the overall project (the graph of connected nodes, project settings) is saved.
*   **Details:**
    *   The project file should reference custom blocks by their names/paths within the project's `atlasvibe_blocks/` directory.
*   **Implementation:**
    *   Added version field to Project type (v2.0.0)
    *   Custom blocks now have `isCustom` and `path` properties
    *   Created project migration utilities for backward compatibility
    *   Updated useLoadApp hook to handle migrations
    *   Added comprehensive tests for custom block references
    *   Tests for multiple custom blocks with unique paths
    *   Tests for project format migration from v1 to v2
    *   Updated saveProject to include version field
    *   Created integration tests for full save/load cycle

**Task 2.7: Visual Indicators and UI Features** ✅ COMPLETED (TDD Methodology)
*   **Action:** Implement UI features for better custom block management and project status
*   **Implementation:**
    *   **Block Regeneration Visual Feedback:**
        - Added visual indicators when blocks are being regenerated
        - Implemented in DefaultBlock component with blinking animation
        - Shows "Regenerating..." label during metadata regeneration
        - Orange border animation while processing
    *   **Blueprint Management:**
        - Added "Save as blueprint" option in block context menu
        - Implemented blueprint name dialog with overwrite confirmation
        - Backend API endpoint for blueprint creation
        - Frontend integration with success notifications
    *   **Project Save Status:**
        - Added status indicator showing save/modified state
        - Autosave functionality with transaction queue
        - Visual feedback for pending saves
        - Error handling with user notifications
    *   **Comprehensive Testing:**
        - Created 5 new Playwright E2E test files following TDD methodology
        - Covers all visual indicators and user interactions
        - Includes edge cases and error scenarios

**Task 2.8: Code Quality Improvements** ✅ COMPLETED (TDD Methodology)
*   **Action:** Improve code maintainability and fix technical debt
*   **Implementation:**
    *   **Shared Docstring Utilities:**
        - Extracted common docstring parsing logic into `docstring_utils.py`
        - Eliminated code duplication across multiple modules
        - Added comprehensive error handling with specific exceptions
        - Added UTF-8 encoding specification for all file operations
        - Improved type hints using specific types instead of Any
        - Created 24 comprehensive tests covering all functionality
    *   **Import Namespace Fix:**
        - Fixed 'atlasvibe' import redirection in build_manifest.py
        - Added custom import hook for proper package resolution
        - Fixed __build_class__ missing in custom builtins
        - Created 9 tests for import redirection scenarios
    *   **IPC Handler Constants:**
        - Replaced string literals with API constants in Electron IPC
        - Improved maintainability and type safety
        - Created 7 tests for IPC handler registration
    *   **Manifest Generation Improvements:**
        - Fixed docstring extraction for custom "Inputs" sections
        - Improved parameter description handling
        - Fixed all 14 manifest generation tests

## Phase 3: Enhanced Code Editor and Virtual Environment Management ✅ COMPLETED

This phase focused on improving the code editor with advanced linting, code completion, error display, and robust virtual environment management.

### Task 3.1: Backend Infrastructure for Code Intelligence ✅ COMPLETED
*   **Action:** Created backend services for code validation and intelligence
*   **Implementation:**
    *   [x] Created `/captain/utils/python_validator.py` for AST-based syntax validation
        - Python AST parsing for accurate syntax checking
        - Type annotation validation
        - Import resolution and validation
        - Variable usage analysis
        - AtlasVibe-specific validation rules (decorator usage, docstring format)
    *   [x] Created `/captain/utils/code_intelligence.py` for code analysis
        - Extract symbols (functions, classes, variables, imports)
        - Analyze type hints and function signatures
        - Generate context-aware completions
        - Parse and validate NumPy-style docstrings
    *   [x] Created API endpoints:
        - `/blocks/validate-code/` - Real-time code validation
        - `/blocks/get-completions/` - Context-aware code completions
        - `/blocks/format-code/` - Code formatting with Black

### Task 3.2: Virtual Environment Management System ✅ COMPLETED
*   **Action:** Implemented comprehensive venv management with detailed logging
*   **Implementation:**
    *   [x] Created `/captain/utils/venv_manager.py` with comprehensive checks:
        - **Pre-regeneration checks:**
            - Python version compatibility (3.8-3.11 support)
            - Dependency conflict detection before installation
            - Disk space availability (min 500MB)
            - Write permissions in project directory
            - Network connectivity for PyPI access
            - UV tool availability and version
        - **During regeneration:**
            - Package download verification with checksums
            - Dependency resolution progress tracking
            - Installation success validation for each package
            - Post-install script execution monitoring
            - Environment activation test
        - **Post-regeneration:**
            - Import test for all dependencies
            - Version compatibility verification
            - Runtime detection (GPU/CPU, memory requirements)
            - Block execution dry-run test
    *   [x] Created structured logging system:
        - JSON-formatted logs with timestamps
        - Step-by-step regeneration progress
        - Error categorization and recovery suggestions
        - Log rotation (keep last 10 regenerations)
    *   [x] Added API endpoints:
        - `/blocks/regenerate-venv/` - Trigger venv regeneration
        - `/blocks/venv-logs/` - Retrieve regeneration logs
        - `/blocks/venv-status/` - Get current venv status

### Task 3.3: Frontend Editor Enhancements ✅ COMPLETED
*   **Action:** Improved the code editor UI with advanced features
*   **Implementation:**
    *   [x] **Error Display Panel:**
        - Added collapsible error panel at editor bottom
        - Scrollable area for multiple errors
        - Error categorization (Syntax, Import, Type, Docstring, Runtime)
        - Click-to-navigate to error line
        - Detailed error explanations with fix suggestions
    *   [x] **Enhanced Linting Integration:**
        - WebSocket connection for real-time validation
        - Display Python AST errors inline
        - Show import resolution errors
        - Type checking with mypy integration
        - Quick-fix suggestions via CodeMirror
    *   [x] **Intelligent Code Completion:**
        - Dynamic completions from backend analysis
        - Import auto-completion with installed packages
        - Method/attribute completions for classes
        - Parameter hints with type information
        - Docstring template generation
    *   [x] **UI Status Indicators:**
        - Virtual environment health status
        - Regeneration progress bar
        - "View Environment" button in block menu
        - VenvStatusDialog component for detailed venv information
        - Code formatting button

### Task 3.4: Docstring Validation System ✅ COMPLETED
*   **Action:** Implemented comprehensive docstring validation for AtlasVibe blocks
*   **Implementation:**
    *   [x] Validate NumPy-style format requirements:
        - Short description on first line
        - Parameters section with proper formatting
        - Returns section with type information
        - Proper indentation and spacing
    *   [x] Generate helpful error messages:
        - "Missing Parameters section in docstring"
        - "Parameter 'x' in function signature not documented"
        - "Invalid parameter format, expected 'name : type'"
        - "Returns section missing type information"
    *   [x] Provide auto-fix suggestions and templates

### Task 3.5: Comprehensive Testing Suite ✅ COMPLETED
*   **Action:** Created extensive Playwright tests for all editor features
*   **Test Scenarios:**
    *   [x] **Basic Editor Functionality:**
        - Code editing and saving
        - Syntax highlighting
        - Undo/redo operations
    *   [x] **Linting and Validation:**
        - Syntax error detection
        - Import error handling
        - Docstring validation
        - Real-time error updates
    *   [x] **Code Completion:**
        - Keyword completion
        - Import suggestions
        - Method completions
        - Parameter hints
    *   [x] **Error Panel:**
        - Error display and navigation
        - Multiple error handling
        - Error filtering
    *   [x] **Venv Management:**
        - Regeneration workflow
        - Progress indication
        - Error recovery
        - Log viewing
    *   [x] **Edge Cases:**
        - Large files (>10k lines)
        - Malformed Python code
        - Network failures during package installation
        - Disk space exhaustion
        - Permission errors
        - Unicode and special characters

### Task 3.6: Error Message Guidelines ✅ COMPLETED
*   **Action:** Created user-friendly error messages
*   **Categories:**
    *   **Syntax Errors:** Clear indication of what's wrong and how to fix
    *   **Import Errors:** Suggest package installation or correct import path
    *   **Type Errors:** Explain type mismatches with examples
    *   **Docstring Errors:** Show correct format with templates
    *   **Venv Errors:** Actionable steps for resolution

## Phase 5: Code Quality and Security Improvements (December 2024) ✅ COMPLETED

This phase focused on improving code quality, security, and maintainability following TDD methodology.

### Task 5.1: Security Fixes ✅ COMPLETED
*   **Action:** Fixed critical security vulnerabilities
*   **Implementation:**
    *   [x] Fixed command injection vulnerability in PingTab.tsx
        - Added comprehensive IP address validation with regex patterns
        - Prevented shell metacharacter injection
        - Added proper error handling for invalid inputs

### Task 5.2: Resource Management ✅ COMPLETED
*   **Action:** Implemented proper cleanup for hardware resources
*   **Implementation:**
    *   [x] Added mecademic robot handle cleanup on shutdown
        - Implemented `cleanup_mecademic_handles()` function
        - Added atexit and signal handlers in main.py
        - Ensures proper disconnection of robot handles

### Task 5.3: Error Handling Improvements ✅ COMPLETED
*   **Action:** Fixed missing error handling across the application
*   **Implementation:**
    *   [x] Fixed missing error handling in control-panel-view.tsx
        - Added null checks for widgetBlockInfo
        - Added toast notifications for errors
        - Improved user feedback

### Task 5.4: TypeScript Type Safety ✅ COMPLETED
*   **Action:** Replaced all TypeScript 'any' types with proper type definitions
*   **Implementation:**
    *   [x] Created comprehensive venv.ts types file
        - CheckStatus enum for venv check states
        - VenvStatus, VenvLog, CheckResult interfaces
        - RegenerateVenvResult and GetVenvLogsResponse types
    *   [x] Fixed all 'any' types in critical components:
        - VenvStatusDialog.tsx - proper state and prop typing
        - BlueprintManagerDialog.tsx - TreeNode discrimination
        - api.ts - ResultAsync return types for all venv functions
        - project.ts - proper error handling with unknown type
    *   [x] Replaced catch(e: any) with catch(e: unknown) pattern
    *   [x] Fixed async function return types to use ResultAsync

### Task 5.5: Shared Utilities Creation ✅ COMPLETED
*   **Action:** Created reusable utility modules to reduce code duplication
*   **Implementation:**
    *   [x] Created `/captain/utils/shared/json_utils.py`:
        - `load_json_file()` with error handling and defaults
        - `save_json_file()` with atomic write support
        - `update_json_file()` for partial updates
        - `merge_json_files()` for combining JSON files
        - 20 comprehensive unit tests
    *   [x] Created `/captain/utils/shared/path_utils.py`:
        - Block path getter functions (python file, metadata, app, etc.)
        - `find_project_root()` for project discovery
        - `ensure_directory_exists()` with parent creation
        - `safe_path_join()` for cross-platform paths
        - `find_files_by_pattern()` for file discovery
        - 33 comprehensive unit tests
    *   [x] Created `/captain/utils/shared/error_utils.py`:
        - `safe_execute()` for safe function execution
        - `with_error_handling` decorator
        - `with_retry` decorator with backoff
        - `error_context` context manager
        - `ErrorAccumulator` for batch error collection
        - 33 comprehensive unit tests
    *   [x] Total: 86 unit tests following TDD methodology

## Phase 6: Refactoring and Technical Debt (Next Priority)

This phase focuses on applying the shared utilities across the codebase and addressing remaining technical debt.

### Task 6.1: JSON Operations Refactoring
*   **Action:** Replace all direct JSON operations with shared utilities
*   **Files to Update:**
    *   [ ] `/captain/utils/block_metadata_generator.py` - Use save_json_file()
    *   [ ] `/captain/utils/project_structure.py` - Use save_json_file()
    *   [ ] `/captain/utils/venv_manager.py` - Use save_json_file() with atomic writes
    *   [ ] `/captain/routes/test_profile.py` - Use error handling utilities
    *   [ ] `/captain/routes/blocks.py` - Use consistent JSON responses
    *   [ ] `/PYTHON/utils/flow_utils.py` - Use save_json_file()
*   **TDD Approach:**
    *   Write tests for each module's JSON operations
    *   Refactor to use shared utilities
    *   Ensure atomic writes where appropriate

### Task 6.2: Error Handling Standardization
*   **Action:** Apply shared error utilities across the codebase
*   **Patterns to Implement:**
    *   [ ] Use `with_error_handling` decorator for all API endpoints
    *   [ ] Use `safe_execute` for non-critical operations
    *   [ ] Use `error_context` for better error messages in complex operations
    *   [ ] Implement `with_retry` for network operations and external services
*   **Files with Generic Exception Handling:**
    *   [ ] Replace `except Exception as e:` patterns with specific handling
    *   [ ] Add proper logging with error context
    *   [ ] Provide user-friendly error messages

### Task 6.3: TODO Items Resolution
*   **Action:** Address all TODO comments in the codebase
*   **High Priority TODOs:**
    *   [ ] Async migration for mecademic_state modules
    *   [ ] Fix OpenCV permission issue on MacOS (hardware.py)
    *   [ ] Support parallel test execution (run_test_sequence.py)
    *   [ ] Add more datasets to TEXT_DATASET block
*   **Medium Priority TODOs:**
    *   [ ] Support multiple inputs/outputs for ONNX_MODEL
    *   [ ] Consolidate REMOTE_FILE and LOCAL_FILE blocks
    *   [ ] Fix block searchbar in keyboard shortcuts test

### Task 6.4: Missing Features Implementation
*   **Action:** Implement identified missing features
*   **Matrioskas (Nested Workflows):**
    *   [ ] Design data model for Matrioskas
    *   [ ] Create API endpoints for Matrioska management
    *   [ ] Implement UI for creating and editing Matrioskas
    *   [ ] Add support for nested execution with loop/cron behavior
    *   [ ] Create comprehensive tests

### Task 6.5: Performance Optimizations
*   **Action:** Optimize critical paths for better performance
*   **Areas to Optimize:**
    *   [ ] Virtual environment creation caching
    *   [ ] Block manifest generation caching
    *   [ ] Parallel block execution where possible
    *   [ ] Frontend bundle size optimization
    *   [ ] WebSocket message batching

## Phase 7: AI Agent Capabilities (Future)

This phase will focus on the long-term goal of transforming nodes into AI agents capable of generating their own Python code.

*   **Task 7.1: Research and Prototyping**
    *   Investigate suitable LLMs or code generation models
    *   Define interaction protocols for agents
    *   Develop UI/UX for managing AI-driven code generation
*   **Task 7.2: Implementation**
    *   Create agent framework for code generation
    *   Implement prompt engineering system
    *   Add version control for AI-generated code
    *   Create safety mechanisms and validation

## Phase 4: Simplified Packaging and Distribution ✅ COMPLETED

**Task 4.1: Remove ASAR Packaging** ✅ COMPLETED
*   **Action:** Eliminate ASAR packaging to simplify file access and development
*   **Implementation:**
    *   Set `asar: false` in electron-builder.yaml
    *   Updated all `process.resourcesPath` references to use app directory
    *   Modified path resolution in consts.ts, executor.ts, utils.ts, and python/index.ts
    *   Electron app now runs with unpacked files for easier debugging

**Task 4.2: Create Python Package Structure** ✅ COMPLETED
*   **Action:** Transform AtlasVibe into a standard pip-installable Python package
*   **Implementation:**
    *   Created `atlasvibe` package with CLI entry points
    *   Added `atlasvibe.cli` module with commands: run, server, ui, init
    *   Created build_hooks.py for bundling Electron app with Python package
    *   Updated pyproject.toml with script entry points
    *   Created MANIFEST.in for proper file inclusion
    *   Created install.sh for easy installation from source

**Task 4.3: Unified Distribution** ✅ COMPLETED
*   **Benefits:**
    *   Single `pip install atlasvibe` command for full installation
    *   No platform-specific Electron builds needed
    *   Python and JavaScript code in same package
    *   Simplified deployment and version management
    *   Better integration between frontend and backend

## General Considerations

*   **Virtual Environments:** The existing per-node venv approach needs to be compatible with the new custom block structure. Ensure that when a custom block is created, its venv setup is also handled correctly using uv. Only uv must be used as environment manager.
*   **Metadata Generation:** The scripts/logic responsible for generating `app.json`, `block_data.json`, etc., must be adapted to work with on-the-fly created custom blocks and potentially modified code.
*   **Testing:** Develop a robust testing strategy for all new functionalities, especially the block creation and editing workflows.
*   **User Experience (UX):** Prioritize an intuitive and clear UX for the new block management and project system.
*   **Backwards Compatibility:** Projects created with the old system will likely not be compatible. This should be clearly communicated.
*   **Package Distribution:** The new pip-based distribution simplifies installation but requires proper testing of the bundled Electron app across platforms.

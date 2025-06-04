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

**Task 2.4: Project-Scoped Block Loading and Management**
*   **Action:** Modify the application to discover and load blocks primarily from the active project's `atlasvibe_blocks/` directory.
*   **Details:**
    *   The application should also be able to access the "blueprint" blocks for creation purposes but not execute them directly in a flow.
    *   The UI for selecting blocks should clearly distinguish between adding a new custom block (from a blueprint) and potentially reusing an existing custom block within the same project.

**Task 2.5: In-IDE Block Code Editing and Synchronization**
*   **Action:** Enable users to edit the Python code of their custom blocks directly within the atlasvibe IDE.
*   **Details:**
    *   Each node representing a custom block should have an "Edit Code" option.
    *   When code is saved:
        1.  The corresponding Python file in the project's `atlasvibe_blocks/` directory is updated.
        2.  A process to regenerate metadata (`app.json`, `block_data.json`) for that specific custom block is triggered. This might involve re-parsing the Python file for the `@atlasvibe` decorator and its parameters.

**Task 2.6: Data Persistence and Project Files**
*   **Action:** Define how the overall project (the graph of connected nodes, project settings) is saved.
*   **Details:**
    *   The project file should reference custom blocks by their names/paths within the project's `atlasvibe_blocks/` directory.

## Phase 3: AI Agent Capabilities (Future - Placeholder)

This phase will focus on the long-term goal of transforming nodes into AI agents capable of generating their own Python code.

*   **Task 3.1: Research and Prototyping**
    *   Investigate suitable LLMs or code generation models.
    *   Define interaction protocols for agents.
    *   Develop UI/UX for managing AI-driven code generation (prompts, suggestions, versioning).
*   **Detailed planning for this phase will occur after Phases 1 and 2 are substantially complete.**

## General Considerations

*   **Virtual Environments:** The existing per-node venv approach needs to be compatible with the new custom block structure. Ensure that when a custom block is created, its venv setup is also handled correctly using uv. Only uv must be used as environment manager.
*   **Metadata Generation:** The scripts/logic responsible for generating `app.json`, `block_data.json`, etc., must be adapted to work with on-the-fly created custom blocks and potentially modified code.
*   **Testing:** Develop a robust testing strategy for all new functionalities, especially the block creation and editing workflows.
*   **User Experience (UX):** Prioritize an intuitive and clear UX for the new block management and project system.
*   **Backwards Compatibility:** Projects created with the old system will likely not be compatible. This should be clearly communicated.


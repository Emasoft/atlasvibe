# atlasvibe

**🚧 Work in Progress: This project is currently under active development and is not yet ready for use. 🚧**

atlasvibe is an upcoming open-source, general-purpose visual programming IDE for Python. It aims to provide a flexible environment for creating Python-based workflows, with a future-forward approach towards AI-assisted node/agent development.

## Vision

The goal is to create an intuitive visual IDE where users can construct complex Python applications by connecting nodes (or "agents"). Each node will represent a Python script, and a core design principle is to eventually empower these nodes with AI capabilities to self-generate or modify their underlying code based on user intent.

## Current Status

atlasvibe is in the early stages of development. The immediate focus is on:
1.  Refactoring the codebase from its origins (see Acknowledgments).
2.  Implementing a new project and block management system where users create project-specific, customizable blocks from a set of blueprints.

## Acknowledgments and Origins

atlasvibe is forked from **Flojoy Studio**, an open-source test sequencer for hardware validation. We are immensely grateful to the original developers of Flojoy Studio for their foundational work and for making it available under the MIT license.

atlasvibe is being developed by **Emasoft** (repository: [Emasoft/atlasvibe](https://github.com/Emasoft/atlasvibe)) and aims to build upon this foundation for a different set of goals, while respecting all original licensing obligations.

## Quickstart

Installation and usage instructions will be provided once the project reaches a more stable state. Currently, it is not recommended for general use.

To set up the Python environment using `uv`:
1.  Ensure you have `uv` installed. See [uv installation guide](https://github.com/astral-sh/uv#installation).
2.  Create and activate a virtual environment:
    ```bash
    uv venv
    source .venv/bin/activate  # On Linux/macOS
    # .venv\Scripts\activate    # On Windows
    ```
3.  Install dependencies:
    ```bash
    uv sync
    ```
    For development dependencies:
    ```bash
    uv sync --all-extras # Or specify extras like 'dev'
    ```

## Running Tests

The project includes both backend (Python) and frontend (TypeScript/Playwright) tests.
You can run all tests using the `runtests.sh` script in the project root:
```bash
bash runtests.sh
```
This script will set up the `uv` environment, install dependencies, and then execute both Python (`pytest`) and Playwright tests.

To run Python tests manually (after setting up the environment and installing dev dependencies):
```bash
uv run pytest .
```

To run Playwright E2E tests manually:
```bash
npx playwright test
```

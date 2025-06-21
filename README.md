# AtlasVibe

**🚧 Work in Progress: This project is currently under active development and is not yet ready for general use. 🚧**

![CI](https://github.com/Emasoft/atlasvibe/workflows/CI/badge.svg)
![Gitleaks](https://github.com/Emasoft/atlasvibe/workflows/Gitleaks%20Security%20Scan/badge.svg)
![Pre-commit](https://github.com/Emasoft/atlasvibe/workflows/Pre-commit%20Checks/badge.svg)
![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

AtlasVibe is an upcoming open-source, general-purpose visual programming IDE for Python. It provides a flexible environment for creating Python-based workflows through a node-based interface, with a future-forward approach towards AI-assisted node/agent development.

## Table of Contents

- [Vision](#vision)
- [Current Status](#current-status)
- [System Requirements](#system-requirements)
- [Installation](#installation)
  - [Installing from Source](#installing-from-source)
  - [Installing from PyPI](#installing-from-pypi)
  - [Developer Installation](#developer-installation)
- [Usage](#usage)
  - [CLI Reference](#cli-reference)
  - [Quick Start](#quick-start)
  - [Running Tests](#running-tests)
- [Development](#development)
  - [Setting Up Development Environment](#setting-up-development-environment)
  - [CI/CD Pipeline](#cicd-pipeline)
  - [Pre-commit Hooks](#pre-commit-hooks)
  - [Contributing](#contributing)
- [Acknowledgments](#acknowledgments)

## Vision

The goal is to create an intuitive visual IDE where users can construct complex Python applications by connecting nodes (or "agents"). Each node represents a Python script, and a core design principle is to eventually empower these nodes with AI capabilities to self-generate or modify their underlying code based on user intent.

## Current Status

AtlasVibe is in the early stages of development. The immediate focus is on:
1. Refactoring the codebase from its origins (see Acknowledgments)
2. Implementing a new project and block management system where users create project-specific, customizable blocks from a set of blueprints
3. Establishing robust CI/CD pipelines and development workflows

## System Requirements

- **Python**: 3.11 or higher
- **Node.js**: 20.x or higher
- **Operating Systems**: macOS, Linux, Windows
- **Memory**: 4GB RAM minimum (8GB recommended)
- **Storage**: 2GB free space

### Additional Requirements for Development

- **Git**: For version control
- **GitHub CLI (`gh`)**: For CI/CD setup
- **uv**: Modern Python package manager (will be installed automatically)

## Installation

### Installing from Source

This is the recommended method during the development phase:

```bash
# Clone the repository
git clone https://github.com/Emasoft/atlasvibe.git
cd atlasvibe

# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Run the installation script
./install.sh

# The installation script will:
# 1. Check system requirements
# 2. Install uv package manager
# 3. Create Python virtual environment
# 4. Install Python dependencies
# 5. Install Node.js dependencies
# 6. Build the Electron application
# 7. Install AtlasVibe as a Python package

# After installation, AtlasVibe will be available as a command
atlasvibe --help
```

#### Manual Installation from Source

If you prefer to install manually or the installation script fails:

```bash
# 1. Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Create and activate virtual environment
uv venv
source .venv/bin/activate  # On Linux/macOS
# .venv\Scripts\activate    # On Windows

# 3. Install Python dependencies
uv sync --all-extras --dev

# 4. Install Node.js dependencies
pnpm install  # or: npm install

# 5. Build the Electron app
pnpm run build
pnpm run electron-package:mac   # On macOS
# pnpm run electron-package:win   # On Windows
# pnpm run electron-package:linux # On Linux

# 6. Install AtlasVibe package
uv pip install -e .
```

### Installing from PyPI

**Note: Not yet available on PyPI. This will be enabled once the project reaches a stable release.**

```bash
# Future installation method (not yet available)
uv pip install atlasvibe
```

### Developer Installation

For development, you'll need additional setup:

```bash
# Clone with submodules
git clone --recursive https://github.com/Emasoft/atlasvibe.git
cd atlasvibe

# Set up git configuration
./setup-git-env.sh

# Install with development dependencies
uv sync --all-extras --dev

# Install pre-commit hooks
uv pip install pre-commit
pre-commit install

# Set up CI/CD pipeline (requires GitHub CLI)
./setup-cicd.sh
```

## Usage

### CLI Reference

AtlasVibe provides a command-line interface for managing the application:

```
atlasvibe --help

Usage: atlasvibe [OPTIONS] COMMAND [ARGS]...

  AtlasVibe - Visual Programming IDE for Python.

Options:
  --version  Show the version and exit.
  --help     Show this message and exit.

Commands:
  init    Initialize a new AtlasVibe project.
  run     Run both server and UI (default command).
  server  Run the AtlasVibe backend server.
  ui      Run the AtlasVibe Electron UI.
```

#### Command Details

##### `atlasvibe run`
Runs both the backend server and Electron UI (recommended for most users).

```bash
atlasvibe run
# Starts the backend server on port 5392
# Launches the Electron UI application
```

##### `atlasvibe server`
Runs only the backend FastAPI server.

```bash
atlasvibe server [OPTIONS]

Options:
  --port INTEGER    Port to run the server on [default: 5392]
  --log-level TEXT  Logging level [default: INFO]

Examples:
  atlasvibe server                    # Run on default port 5392
  atlasvibe server --port 8080       # Run on custom port
  atlasvibe server --log-level DEBUG # Enable debug logging
```

##### `atlasvibe ui`
Runs only the Electron UI application.

```bash
atlasvibe ui [OPTIONS]

Options:
  --dev  Run in development mode

Examples:
  atlasvibe ui       # Run production build
  atlasvibe ui --dev # Run with hot reload (requires source installation)
```

##### `atlasvibe init`
Creates a new AtlasVibe project directory structure.

```bash
atlasvibe init PATH

Arguments:
  PATH  Path where the new project should be created

Example:
  atlasvibe init my-workflow
  # Creates:
  # my-workflow/
  # ├── atlasvibe_blocks/    # Custom blocks directory
  # ├── flows/               # Workflow files directory
  # └── project.atlasvibe    # Project configuration
```

### Quick Start

1. **Create a new project:**
   ```bash
   atlasvibe init my-first-project
   cd my-first-project
   ```

2. **Start AtlasVibe:**
   ```bash
   atlasvibe run
   ```

3. **Access the application:**
   - The UI will open automatically
   - Backend API available at: http://localhost:5392
   - API documentation at: http://localhost:5392/docs

4. **Create your first workflow:**
   - Drag blocks from the palette
   - Connect blocks to create data flow
   - Click "Run" to execute the workflow

### Running Tests

AtlasVibe includes comprehensive test suites for both backend and frontend:

```bash
# Run all tests using the test script
./runtests.sh

# Run Python tests only
uv run pytest

# Run specific test file
uv run pytest tests/test_file.py

# Run with coverage
uv run pytest --cov --cov-report=html

# Run frontend tests
pnpm test

# Run E2E tests
pnpm run e2e

# Run ALL tests including slow tests
./install_all_test_deps.sh  # First time only
./run_all_tests.sh
```

## Development

### Setting Up Development Environment

1. **Install development dependencies:**
   ```bash
   uv sync --all-extras --dev
   pnpm install
   ```

2. **Set up pre-commit hooks:**
   ```bash
   uv pip install pre-commit
   pre-commit install
   ```

3. **Configure git:**
   ```bash
   ./setup-git-env.sh
   ```

4. **Run in development mode:**
   ```bash
   # Terminal 1: Backend with auto-reload
   uv run python main.py --reload

   # Terminal 2: Frontend with hot reload
   pnpm run dev
   ```

### CI/CD Pipeline

AtlasVibe uses GitHub Actions for continuous integration and deployment:

#### GitHub Actions Workflows

1. **CI Pipeline** (`.github/workflows/ci.yml`)
   - Python code formatting and linting (Ruff)
   - TypeScript/JavaScript checks (ESLint, TSC, Prettier)
   - Unit tests with coverage reporting
   - Runs on every push and pull request

2. **Security Scanning** (`.github/workflows/gitleaks.yml`)
   - Scans for secrets in code
   - Runs on every push, PR, and daily schedule
   - Creates security alerts for any findings

3. **Dependency Analysis** (`.github/workflows/dependency-check.yml`)
   - Weekly scans with deptry
   - Identifies unused or missing dependencies
   - Creates issues for problems

4. **Pre-commit Checks** (`.github/workflows/pre-commit.yml`)
   - Runs all pre-commit hooks in CI
   - Validates code quality
   - Comments on PRs with results

5. **Blocks Quality** (`.github/workflows/blocks-quality-check.yml`)
   - Ensures all blocks have required metadata
   - Runs block-specific tests
   - Validates block structure

#### Setting Up CI/CD

Run the setup script to configure GitHub repository settings:

```bash
# Requires GitHub CLI (gh) to be installed and authenticated
gh auth login

# Run the CI/CD setup
./setup-cicd.sh

# This will:
# - Configure repository settings
# - Set up branch protection
# - Create issue labels
# - Configure security scanning
# - Set up workflow permissions
```

### Pre-commit Hooks

The project uses pre-commit hooks to ensure code quality:

```yaml
# .pre-commit-config.yaml includes:
- uv-lock: Keeps lockfile updated
- ruff: Python linting and formatting
- gitleaks: Secret detection
- deptry: Dependency analysis
- yamllint: YAML validation
- Various file checks
```

To run hooks manually:
```bash
# Run on all files
pre-commit run --all-files

# Run specific hook
pre-commit run ruff --all-files

# Update hooks to latest versions
pre-commit autoupdate
```

### Contributing

We welcome contributions! Please follow these guidelines:

1. **Code Style:**
   - Python: Follow Ruff formatting (automatically applied)
   - TypeScript: Follow ESLint and Prettier rules
   - Commit messages: Use conventional commits format

2. **Testing:**
   - Write tests for new features
   - Ensure all tests pass before submitting PR
   - Maintain or improve code coverage

3. **Documentation:**
   - Update documentation for API changes
   - Add docstrings to new functions
   - Update README for new features

4. **Security:**
   - Never commit secrets or credentials
   - Use environment variables for sensitive data
   - Follow security best practices

5. **Pull Requests:**
   - Create feature branches from `main`
   - Keep PRs focused and atomic
   - Include tests and documentation
   - Ensure CI passes before review

## Acknowledgments

AtlasVibe is forked from **Flojoy Studio**, an open-source test sequencer for hardware validation. We are immensely grateful to the original developers of Flojoy Studio for their foundational work and for making it available under the MIT license.

AtlasVibe is being developed by **Emasoft** (repository: [Emasoft/atlasvibe](https://github.com/Emasoft/atlasvibe)) and aims to build upon this foundation for a different set of goals, while respecting all original licensing obligations.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/Emasoft/atlasvibe/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Emasoft/atlasvibe/discussions)
- **Security**: For security issues, please see [SECURITY.md](SECURITY.md)

---

**Note**: AtlasVibe is under active development. APIs and features may change. We recommend waiting for a stable release before using in production environments.

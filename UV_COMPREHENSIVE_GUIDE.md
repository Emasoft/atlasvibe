# Comprehensive UV Package Management Guide for AtlasVibe

## Core UV Concepts

### 1. Environment Management Philosophy
- **Always use virtual environments** - UV enforces this by default
- **Never modify system Python** - Requires explicit `--system` flag
- **Environments are disposable** - Recreate rather than repair

### 2. Environment Discovery Order
1. Active `VIRTUAL_ENV` environment variable
2. Active Conda environment
3. `.venv` in current directory or parent directories
4. Prompts to create if none found

### 3. Project vs Standalone Mode
- **Project mode**: Has `pyproject.toml`, uses `uv sync` and `uv run`
- **Standalone mode**: No project file, uses `uv pip` commands directly

## Complete UV Workflow for AtlasVibe

### Step 1: Initial Project Setup

```bash
# 1. Create new project (if starting fresh)
uv init --app                    # For applications
uv init --lib                    # For libraries
uv init --build-backend uv       # With uv build backend (preview)

# 2. For existing project, ensure Python version
uv python install 3.11           # Download Python if needed
uv python pin 3.11               # Create .python-version file

# 3. Create virtual environment
uv venv                          # Creates .venv in current directory
uv venv --python 3.11            # With specific Python version
```

### Step 2: Dependency Management

#### A. Project Dependencies (pyproject.toml)

```toml
[project]
name = "atlasvibe"
version = "0.1.0"
description = "Visual programming IDE"
requires-python = ">=3.11,<3.13"
dependencies = [
    "fastapi>=0.104.1",
    "pydantic>=2.11.4",
    "numpy>=1.23.0",
]

[project.optional-dependencies]
# Published extras (for users)
plotting = ["matplotlib>=3.5", "seaborn>=0.12"]
hardware = ["pyserial>=3.5", "pyvisa>=1.13"]

[dependency-groups]
# Development dependencies (not published)
dev = [
    "pytest>=7.4.0",
    "ruff>=0.4.0",
    "mypy>=1.0.0",
]
test = [
    "pytest-cov>=5.0.0",
    "pytest-mock>=3.11.0",
]
docs = [
    "mkdocs>=1.5.0",
    "mkdocs-material>=9.0",
]

[tool.uv]
# UV-specific configuration
default-groups = ["dev"]  # Groups to install by default
managed = true           # Let uv manage the environment

[tool.uv.sources]
# Alternative dependency sources
my-package = { workspace = true }
custom-lib = { path = "./libs/custom" }
private-pkg = { git = "https://github.com/org/private.git", branch = "main" }
```

#### B. Adding Dependencies

```bash
# Add to main dependencies
uv add numpy pandas scikit-learn

# Add with version constraints
uv add "fastapi>=0.100.0,<1.0.0"

# Add to optional dependencies (extras)
uv add --optional plotting matplotlib seaborn

# Add to dependency groups (dev dependencies)
uv add --group dev pytest ruff
uv add --group test pytest-cov

# Add from various sources
uv add git+https://github.com/user/repo
uv add --editable ./local/package
uv add package@https://files.example.com/package.whl
```

#### C. Installing Dependencies

```bash
# Sync project environment (recommended)
uv sync                          # Install default dependencies + default groups
uv sync --frozen                 # Use exact versions from lockfile
uv sync --inexact                # Keep extra packages installed

# Install with extras
uv sync --extra plotting         # Include plotting extra
uv sync --all-extras            # Include all extras

# Install specific groups
uv sync --group test            # Include test group
uv sync --no-group dev          # Exclude dev group
uv sync --only-group docs       # Only docs group
uv sync --all-groups           # All groups

# Partial installation
uv sync --no-install-project    # Don't install the project itself
uv sync --no-install-workspace  # Don't install workspace members
```

### Step 3: Lock File Management

```bash
# Create/update lockfile
uv lock                         # Lock all dependencies
uv lock --upgrade              # Upgrade all packages
uv lock --upgrade-package numpy # Upgrade specific package

# Compile requirements (alternative to lock)
uv pip compile pyproject.toml -o requirements.txt
uv pip compile --extra plotting -o requirements-plotting.txt
uv pip compile --all-extras -o requirements-all.txt
```

### Step 4: Running Code

```bash
# Run in project environment
uv run python main.py           # Syncs deps first
uv run --no-sync python main.py # Skip sync
uv run -m pytest               # Run module

# Run with temporary dependencies
uv run --with httpx python script.py
uv run --with "httpx>=0.25" python script.py

# Run scripts with inline metadata
uv run script.py               # Script can declare its own deps

# Run in specific package (workspace)
uv run --package backend pytest
```

### Step 5: Building Distributions

```bash
# Build project distributions
uv build                        # Build wheel and sdist
uv build --wheel               # Build only wheel
uv build --sdist               # Build only source dist

# Build with constraints
uv build --build-constraint constraints.txt
uv build --require-hashes

# Build specific package (workspace)
uv build --package my-lib
```

### Step 6: Inspecting Packages

```bash
# List installed packages
uv pip list                     # All packages
uv pip list --format json      # JSON output

# Show package details
uv pip show numpy pandas       # Multiple packages

# Export to requirements format
uv pip freeze > requirements.txt
uv pip freeze --exclude-editable

# Check for conflicts
uv pip check

# Show dependency tree
uv pip tree                    # Full tree
uv pip tree --package numpy    # Specific package
```

## Workspace Configuration

### Setting Up Workspaces

```toml
# Root pyproject.toml
[tool.uv.workspace]
members = ["packages/*", "apps/*", "libs/*"]
exclude = ["packages/experimental"]

[tool.uv.sources]
# Workspace member dependencies
backend = { workspace = true }
frontend = { workspace = true }
shared = { workspace = true }
```

### Workspace Commands

```bash
# Sync entire workspace
uv sync --all-packages

# Build all packages
uv build --all-packages

# Run in specific member
uv run --package backend pytest
uv run --package frontend npm test
```

## AtlasVibe-Specific Patterns

### 1. Block Virtual Environment Management

Each AtlasVibe block should have its own environment:

```python
# In block's @atlasvibe decorator
@atlasvibe(
    deps=["numpy>=1.20", "pandas>=2.0"],
    pip_install_args=["--index-url", "https://pypi.org/simple"]
)
def MY_BLOCK(...):
    pass
```

UV will create: `blocks/CATEGORY/MY_BLOCK/.venv/`

### 2. Development Workflow

```bash
# Initial setup
uv python install 3.11
uv venv
uv sync --all-extras --dev

# Daily development
uv run python main.py          # Run backend
uv run pnpm run dev           # Run frontend

# Testing
uv run pytest                  # Run tests
uv run --group test pytest -v  # With test group deps

# Building
uv build                       # Build distributions
```

### 3. CI/CD Integration

```yaml
# .github/workflows/ci.yml
- uses: astral-sh/setup-uv@v5
  with:
    enable-cache: true
    cache-dependency-glob: "uv.lock"

- name: Install dependencies
  run: uv sync --locked --all-extras --dev

- name: Run tests
  run: uv run pytest
```

### 4. Pre-commit Integration

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/uv-pre-commit
    rev: 0.7.13
    hooks:
      - id: uv-lock
      - id: uv-export
        args: ["--format", "requirements.txt"]
```

## Configuration Reference

### UV Settings (uv.toml or pyproject.toml)

```toml
[tool.uv]
# Dependency resolution
resolution = "highest"          # or "lowest", "lowest-direct"
prerelease = "if-necessary"     # or "allow", "disallow"
exclude-newer = "2024-01-01"    # Reproducible resolution

# Index configuration
index = ["https://pypi.org/simple"]
extra-index-url = ["https://custom.index/simple"]
find-links = ["https://files.example.com/wheels"]

# Build configuration
no-build = false               # Allow building from source
no-binary = ["package-name"]   # Force source builds
compile-bytecode = true        # Compile .pyc files

# Installation
link-mode = "hardlink"         # or "copy", "clone", "symlink"
reinstall = false
upgrade = false

# Python management
managed = true                 # Use uv-managed Python
python-preference = "managed"  # Prefer uv Python

# Cache
cache-dir = "~/.cache/uv"
no-cache = false
```

## Best Practices

### 1. Always Commit Lockfiles
```bash
git add uv.lock
git commit -m "Update dependencies"
```

### 2. Use Dependency Groups Wisely
- `project.dependencies`: Runtime dependencies
- `project.optional-dependencies`: Published extras
- `dependency-groups`: Development dependencies

### 3. Pin Python Version
```bash
uv python pin 3.11  # Creates .python-version
```

### 4. Regular Updates
```bash
# Weekly/monthly
uv lock --upgrade
uv sync
uv run pytest  # Verify nothing broke
```

### 5. Reproducible Builds
```bash
# Use --frozen in production
uv sync --frozen

# Or use exact resolution date
uv lock --exclude-newer 2024-01-01
```

## Troubleshooting

### Issue: Module not found
```bash
# Ensure environment is synced
uv sync
# Check if in right environment
which python  # Should show .venv/bin/python
```

### Issue: Dependency conflicts
```bash
# Show resolution details
uv pip compile --verbose pyproject.toml
# Try different resolution strategy
uv lock --resolution lowest-direct
```

### Issue: Build failures
```bash
# Build with verbose output
uv build -v
# Skip build isolation
uv build --no-build-isolation
```

### Issue: Platform-specific problems
```bash
# Resolve for specific platform
uv lock --python-platform linux --python-version 3.11
```

## Migration from Poetry/pip

### From Poetry
1. Export requirements: `poetry export -f requirements.txt > requirements.txt`
2. Create pyproject.toml with uv structure
3. Import deps: `uv add -r requirements.txt`
4. Add dev deps: `uv add --group dev -r requirements-dev.txt`

### From pip
1. Generate requirements: `pip freeze > requirements.txt`
2. Create project: `uv init --app`
3. Import deps: `uv add -r requirements.txt`

## Summary: Essential UV Commands for AtlasVibe

```bash
# Setup
uv init --app                  # Create project
uv python install 3.11         # Install Python
uv venv                        # Create environment
uv sync                        # Install dependencies

# Development
uv add package                 # Add dependency
uv run python main.py          # Run code
uv run pytest                  # Run tests
uv lock --upgrade             # Update deps

# Production
uv sync --frozen              # Install exact versions
uv build                      # Build distributions
uv pip install dist/*.whl     # Install built package
```

This guide provides complete UV coverage for AtlasVibe development. UV's philosophy centers on isolated environments, reproducible builds, and fast operations.

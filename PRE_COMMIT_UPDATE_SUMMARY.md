# Pre-commit Hooks Update Summary

## Overview

Updated the `.pre-commit-config.yaml` to ensure ALL GitHub Actions checks run locally before code reaches GitHub, as requested.

## New Hooks Added

### 1. **TypeScript Type Checking**

- Runs `pnpm exec tsc --noEmit` to catch type errors
- Ensures TypeScript code is type-safe before commit

### 2. **UV Pip Dependency Check**

- Runs `uv pip check` to verify dependency consistency
- Catches dependency conflicts early

### 3. **Yamllint**

- Comprehensive YAML validation beyond syntax checking
- Uses `.yamllint` config file for consistent rules

### 4. **Block Sync Check**

- Ensures block metadata is synchronized
- Runs `uv run python -m cli.cmd.sync`
- Prevents commits if block metadata is out of sync
- Uses `scripts/check-block-sync.sh` for clean execution

### 5. **Block-specific Tests**

- Runs pytest specifically on blocks directory
- Ensures block changes don't break tests

## Updated Hooks

### 1. **Ruff Linter**

- Now uses exact ignore rules from CI:
  ```
  E203,E402,E501,E266,W505,F841,F842,F401,W293,I001,UP015,C901,W291
  ```
- Added `--isolated` flag
- Added `--output-format full` for better error messages

### 2. **Ruff Formatter**

- Added `--isolated` flag to match CI

### 3. **Pytest**

- Now includes coverage reporting (`--cov`, `--cov-report=xml`)
- Tests specific directories: `tests/`, `PYTHON/tests/`, `cli/`
- Added `--timeout=60` to match CI
- Added `-v` for verbose output

## Configuration Files Created

### 1. `.yamllint`

- Yamllint configuration with sensible defaults
- Allows 320 character lines to match project style
- Ignores common directories (venv, node_modules, etc.)

### 2. `scripts/check-block-sync.sh`

- Script to check if block metadata is synchronized
- Provides clear error messages when sync is needed

## How It Works

When you commit code, pre-commit will now:

1. **Format Code**:

   - Python with Ruff and Black
   - JavaScript/TypeScript with Prettier
   - YAML with yamlfmt (GitHub workflows only)

2. **Lint Code**:

   - Python with Ruff and MyPy
   - JavaScript/TypeScript with ESLint
   - Shell scripts with shellcheck
   - YAML with yamllint
   - GitHub Actions with actionlint

3. **Check Dependencies**:

   - UV lock file consistency
   - UV pip dependency conflicts
   - Deptry for unused/missing dependencies

4. **Run Tests**:

   - Quick Python tests (excluding slow tests)
   - Block-specific tests when blocks change

5. **Verify Integrity**:
   - Block metadata synchronization
   - TypeScript type safety

## Expected Behavior

- **First run may have failures**: Some hooks may find existing issues that need fixing
- **Automatic fixes**: Many hooks will auto-fix issues (formatting, some linting)
- **Clear error messages**: Each hook provides specific guidance on what needs fixing
- **Fast execution**: Only runs relevant hooks based on changed files

## Maintenance

To update hooks to latest versions:

```bash
pre-commit autoupdate
```

To run all hooks on all files:

```bash
pre-commit run --all-files
```

To bypass hooks temporarily (use sparingly):

```bash
git commit --no-verify -m "Emergency fix"
```

## Result

With these comprehensive pre-commit hooks, code will be thoroughly checked locally before it reaches GitHub, ensuring that GitHub Actions workflows will pass. This addresses the user's requirement: "all linting must be done when commit locally. All formatting and testing hooks must be run when commit locally."

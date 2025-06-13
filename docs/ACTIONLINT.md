# Actionlint Configuration

This repository uses [actionlint](https://github.com/rhysd/actionlint) to validate GitHub Actions workflow files.

## Local Usage

### Installation

On macOS:
```bash
brew install actionlint
```

On other platforms, see the [official installation guide](https://github.com/rhysd/actionlint#install).

### Running actionlint

To check all workflow files:
```bash
actionlint
```

To check specific workflow files:
```bash
actionlint .github/workflows/my-workflow.yml
```

## GitHub Actions Integration

Actionlint runs automatically on:
- Push events that modify workflow files
- Pull requests that modify workflow files
- Manual workflow dispatch

The actionlint workflow will:
1. Check all workflow files for errors
2. Report issues as PR comments (for pull requests)
3. Fail the CI if critical errors are found

## Configuration

The actionlint configuration is in `.github/actionlint.yaml` and includes:
- Shellcheck integration for shell scripts in workflows
- Pyflakes integration for Python scripts in workflows

## Pre-commit Hook

To enable actionlint as a pre-commit hook:
```bash
pip install pre-commit
pre-commit install
```

This will run actionlint on workflow files before each commit.

## Common Issues Found by Actionlint

1. **Outdated action versions**: Update to the latest versions (e.g., `actions/checkout@v4`)
2. **Shell script issues**: Proper quoting and error handling
3. **Invalid workflow syntax**: YAML formatting and workflow structure
4. **Deprecated features**: Outdated GitHub Actions syntax

## Fixing Issues

When actionlint reports issues:
1. Check the error message and line number
2. Fix the issue in the workflow file
3. Run `actionlint` locally to verify the fix
4. Commit and push the changes
# AtlasVibe CI/CD Guide

## Overview

AtlasVibe uses GitHub Actions for continuous integration and deployment with uv package manager.

## Workflows

### Core Workflows

1. **CI Pipeline** (`.github/workflows/ci.yml`)

   - **Triggers**: Push to main, Pull requests
   - **Jobs**:
     - `python-code-format`: Ruff formatting check
     - `python-code-lint`: Ruff linting
     - `python-tests`: Pytest with coverage
     - `ts-code-style`: ESLint, TypeScript, Prettier
     - `check-lockfile`: Verify uv.lock is up-to-date

2. **CD Pipeline** (`.github/workflows/cd.yaml`)

   - **Triggers**: Version tags (v\*), Manual dispatch
   - **Jobs**:
     - `pre-release-checks`: Quality gates before build
     - `buildElectron`: Multi-platform Electron builds

3. **Security Workflows**
   - **Gitleaks** (`.github/workflows/gitleaks.yml`): Secret scanning
   - **Dependency Check** (`.github/workflows/dependency-check.yml`): Weekly vulnerability scans
   - **Pre-commit** (`.github/workflows/pre-commit.yml`): Comprehensive checks

### Local Development

#### Running CI Checks Locally

```bash
# Run all pre-commit hooks
pre-commit run --all-files

# Run specific checks
uv run ruff check .
uv run ruff format .
uv run pytest
uv run mypy .

# Check uv.lock
uv lock --check

# Run gitleaks
gitleaks detect --config .gitleaks.toml
```

#### Working with uv

```bash
# Update all dependencies
uv lock --upgrade

# Update specific package
uv lock --upgrade-package numpy

# Sync environment
uv sync --all-extras --dev

# Add new dependency
uv add package-name

# Add dev dependency
uv add --dev package-name
```

### GitHub CLI Commands

```bash
# View workflows
gh workflow list
gh run list

# Watch a run
gh run watch

# Download artifacts
gh run download [run-id]

# Trigger manual workflow
gh workflow run cd.yaml

# View workflow file
gh workflow view ci.yml
```

### Debugging CI Failures

1. **Check workflow logs**:

   ```bash
   gh run view [run-id] --log
   ```

2. **Re-run failed jobs**:

   ```bash
   gh run rerun [run-id] --failed
   ```

3. **Common issues**:
   - **uv.lock out of sync**: Run `uv lock` locally and commit
   - **Import errors**: Check Python path configuration
   - **Test failures**: Run tests locally with same Python version

### Release Process

1. **Prepare release**:

   ```bash
   # Update version in pyproject.toml
   # Update CHANGELOG.md
   # Commit changes
   ```

2. **Create tag**:

   ```bash
   git tag v0.1.0
   git push origin v0.1.0
   ```

3. **Monitor build**:

   ```bash
   gh run list --workflow cd.yaml
   gh run watch
   ```

4. **Verify release**:
   ```bash
   gh release view v0.1.0
   ```

## Best Practices

1. **Always run pre-commit before pushing**
2. **Keep dependencies updated with `uv lock --upgrade`**
3. **Use conventional commits for clear history**
4. **Test locally with same Python version as CI**
5. **Don't skip CI checks with `--no-verify`**

## Security

- All commits are scanned for secrets
- Dependencies are checked weekly
- Only approved values in git config:
  - Author: Emasoft
  - Email: 713559+Emasoft@users.noreply.github.com

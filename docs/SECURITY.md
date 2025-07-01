# Security Configuration for AtlasVibe

This document describes the security measures implemented in the AtlasVibe project.

## Secret Scanning with TruffleHog

AtlasVibe uses [TruffleHog](https://github.com/trufflesecurity/trufflehog) to prevent secrets from being committed to the repository.

### Configuration

- **Exclude file**: `.trufflehog-exclude` - Regex patterns for paths to exclude
- **Pre-commit hook**: Automatically scans staged files before commit
- **Pre-push hook**: Scans commits before pushing
- **GitHub Actions**: Scans on push, PR, and daily schedule
- **Version**: TruffleHog v3.89.0+

### Excluded Paths

The following paths are excluded from scanning (via `.trufflehog-exclude`):

- Version control: `.git/`
- Dependencies: `node_modules/`, `.venv/`, `venv/`
- Build outputs: `dist/`, `build/`, `out/`
- Caches: `__pycache__/`, `.pytest_cache/`, `.mypy_cache/`
- Lock files: `package-lock.json`, `pnpm-lock.yaml`, `uv.lock`
- Tests and documentation: `tests/`, `*.md`

### Running Manually

```bash
# Scan entire repository (only verified secrets)
trufflehog filesystem . --exclude-paths .trufflehog-exclude --no-update --fail --only-verified

# Scan specific directory
trufflehog filesystem path/to/directory --exclude-paths .trufflehog-exclude --no-update --fail --only-verified

# Scan git history
trufflehog git file://. --exclude-paths .trufflehog-exclude --no-update --fail --only-verified

# Scan all secrets (including unverified)
trufflehog filesystem . --exclude-paths .trufflehog-exclude --no-update --fail
```

### If Secrets Are Detected

1. **DO NOT COMMIT** the changes
2. **Remove the secret** from your code
3. **Replace with environment variable** or secure vault
4. **Rotate the exposed secret** immediately
5. **Update .trufflehog-exclude**: If path should be excluded, add to allow list

## Git Configuration

All commits must use the following identity:

- **Name**: Emasoft
- **Email**: 713559+Emasoft@users.noreply.github.com

This is enforced by:

1. Pre-commit hook verification
2. Shell environment variables
3. Git configuration

## GitHub Actions Security

### Workflows

- **TruffleHog Security Scan**: Runs on every push and PR
- **SARIF Upload**: Security findings uploaded to GitHub Security tab
- **PR Comments**: Automatic comments on security failures
- **Issue Creation**: Creates issues for secrets in pushed commits

### Permissions

All workflows use minimal required permissions:

- `contents: read`
- `security-events: write` (for SARIF upload)
- `pull-requests: write` (for PR comments)

## Development Environment

### Environment Variables

Set in `.envrc` (for direnv) or shell config:

```bash
export GIT_AUTHOR_NAME="Emasoft"
export GIT_AUTHOR_EMAIL="713559+Emasoft@users.noreply.github.com"
export GIT_COMMITTER_NAME="Emasoft"
export GIT_COMMITTER_EMAIL="713559+Emasoft@users.noreply.github.com"
```

### Virtual Environment Management

All Python environments are managed by `uv`:

- No direct use of `venv` module
- Automatic environment creation per block
- Secure dependency installation

## Security Best Practices

1. **Never commit secrets**: Even temporarily or in history
2. **Use environment variables**: For sensitive configuration
3. **Review TruffleHog output**: Don't ignore warnings
4. **Update allow lists carefully**: Document why patterns are safe
5. **Rotate compromised secrets**: Immediately if exposed

## Incident Response

If secrets are detected:

1. **Don't push**: The pre-commit hook will block you
2. **Remove secrets**: From your staged changes
3. **Check history**: Ensure secrets aren't in previous commits
4. **Rotate secrets**: If already pushed, rotate immediately
5. **Update .trufflehog-exclude**: If path should be excluded

## GitHub Repository Settings

Run `./setup-cicd.sh` to verify:

- Branch protection rules
- Security scanning enabled
- Automated security fixes
- Dependency scanning

## Questions or Issues?

- Check the [TruffleHog documentation](https://github.com/trufflesecurity/trufflehog)
- Review `.trufflehog.yaml` for current rules
- Run `./setup-cicd.sh` for setup verification

# Security Configuration for AtlasVibe

This document describes the security measures implemented in the AtlasVibe project.

## Secret Scanning with Gitleaks

AtlasVibe uses [Gitleaks](https://github.com/gitleaks/gitleaks) to prevent secrets from being committed to the repository.

### Configuration

- **Config file**: `.gitleaks.toml`
- **Pre-commit hook**: Automatically scans staged files before commit
- **GitHub Actions**: Scans on push, PR, and daily schedule

### Allowed Patterns

The following patterns are explicitly allowed:
- GitHub noreply email: `713559+Emasoft@users.noreply.github.com`
- Test/example patterns: `test-api-key`, `YOUR_API_KEY_HERE`, etc.
- Placeholder values in documentation

### Running Manually

```bash
# Scan entire repository
gitleaks detect --config .gitleaks.toml --verbose

# Scan staged files only
gitleaks protect --config .gitleaks.toml --staged --verbose

# Scan specific directory
gitleaks detect --config .gitleaks.toml --source path/to/directory
```

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
- **Gitleaks Security Scan**: Runs on every push and PR
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
3. **Review Gitleaks output**: Don't ignore warnings
4. **Update allowlists carefully**: Document why patterns are safe
5. **Rotate compromised secrets**: Immediately if exposed

## Incident Response

If secrets are detected:
1. **Don't push**: The pre-commit hook will block you
2. **Remove secrets**: From your staged changes
3. **Check history**: Ensure secrets aren't in previous commits
4. **Rotate secrets**: If already pushed, rotate immediately
5. **Update .gitleaks.toml**: If false positive

## GitHub Repository Settings

Run `./scripts/github-setup.sh` to verify:
- Branch protection rules
- Security scanning enabled
- Automated security fixes
- Dependency scanning

## Questions or Issues?

- Check the [Gitleaks documentation](https://github.com/gitleaks/gitleaks)
- Review `.gitleaks.toml` for current rules
- Run `./scripts/github-setup.sh` for setup verification
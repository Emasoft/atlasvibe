# Security Configuration for AtlasVibe

This document describes the security measures implemented in the AtlasVibe project.

## Secret Scanning

AtlasVibe uses pre-commit hooks and code review processes to prevent secrets from being committed to the repository.

### Best Practices

1. **Never commit real secrets**: Use environment variables or secure vaults
2. **Use obvious fake values**: For examples, use values like `test-api-key` or `your-api-key-here`
3. **Documentation**: When documenting API usage, always use placeholder values
4. **Review changes**: Always review your staged changes before committing

### If Secrets Are Detected

1. **DO NOT COMMIT** the changes
2. **Remove the secret** from your code
3. **Replace with environment variable** or secure vault
4. **Rotate the exposed secret** immediately

## Git Configuration

All commits must use the following identity:

- **Name**: Emasoft
- **Email**: 713559+Emasoft@users.noreply.github.com

This is enforced by:

1. Pre-commit hook verification
2. Shell environment variables
3. Git configuration

## GitHub Actions Security

### Permissions

All workflows use minimal required permissions:

- `contents: read`
- `security-events: write` (for security scanning)
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
3. **Review pre-commit output**: Don't ignore warnings
4. **Rotate compromised secrets**: Immediately if exposed

## Incident Response

If secrets are accidentally committed:

1. **Don't push**: The pre-commit hook should block you
2. **Remove secrets**: From your staged changes
3. **Check history**: Ensure secrets aren't in previous commits
4. **Rotate secrets**: If already pushed, rotate immediately

## GitHub Repository Settings

Run `./scripts/github-setup.sh` to verify:

- Branch protection rules
- Security scanning enabled
- Automated security fixes
- Dependency scanning

## Questions or Issues?

- Review pre-commit configuration for current rules
- Run `./scripts/github-setup.sh` for setup verification

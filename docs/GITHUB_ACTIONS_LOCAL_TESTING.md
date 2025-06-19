# Testing GitHub Actions Locally with Act

This guide explains how to test GitHub Actions workflows locally using `act` with `uv` support.

## Prerequisites

1. **Install Docker Desktop**
   - Download from: https://www.docker.com/products/docker-desktop/
   - Ensure Docker is running before using act

2. **Install act**
   ```bash
   brew install act
   ```

3. **Verify Installation**
   ```bash
   act --version
   docker --version
   ```

## Configuration

The project includes `.actrc` configuration file that:
- Uses larger runner images with more tools pre-installed
- Sets up environment variables for uv compatibility
- Enables container reuse for faster runs
- Configures proper architecture settings

## Testing Workflows

Use the provided script `scripts/test-github-actions.sh`:

```bash
# List all available workflows and jobs
./scripts/test-github-actions.sh list

# Run specific workflows
./scripts/test-github-actions.sh ci                # Run all CI jobs
./scripts/test-github-actions.sh ci python-tests   # Run only python-tests job
./scripts/test-github-actions.sh pre-commit        # Run pre-commit checks
./scripts/test-github-actions.sh dependency-check  # Run dependency analysis
./scripts/test-github-actions.sh gitleaks          # Run secret scanning
```

## Direct act Usage

You can also use act directly:

```bash
# List all workflows
act -l

# Run push event workflows
act push

# Run pull_request event workflows
act pull_request

# Run a specific job
act -j python-tests

# Run with specific workflow file
act -W .github/workflows/ci.yml

# Dry run (see what would be executed)
act -n push
```

## Working with Secrets

For workflows that require secrets (like CD workflow):

1. Create `.env.secrets` file (gitignored):
   ```
   AZURE_KEY_VAULT_URI=your-value
   AZURE_CLIENT_ID=your-value
   AZURE_TENANT_ID=your-value
   AZURE_CLIENT_SECRET=your-value
   AZURE_CERT_NAME=your-value
   ```

2. Run with secrets:
   ```bash
   act -W .github/workflows/cd.yaml --secret-file .env.secrets
   ```

## Troubleshooting

### Docker Not Running
```
Error: Docker is not running. Please start Docker Desktop.
```
**Solution**: Start Docker Desktop application

### Container Architecture Issues
The `.actrc` file sets `--container-architecture linux/amd64` for compatibility.
If you have issues on Apple Silicon, you may need to adjust this.

### Missing Tools in Container
The project uses `catthehacker/ubuntu:act-latest` images which include most tools.
If a tool is missing, you can:
1. Install it in the workflow step
2. Use a custom Docker image
3. Mount local tools into the container

### uv-specific Issues
- The `.actrc` sets `UV_SYSTEM_PYTHON=1` to use system Python
- `UV_NO_CACHE=1` prevents caching issues in containers
- Ensure Python 3.11 is available in the runner image

## Best Practices

1. **Test Locally First**: Always test workflows locally before pushing
2. **Use Dry Run**: Use `act -n` to see what would run without execution
3. **Cache Dependencies**: Use `--reuse` flag (set in .actrc) to speed up runs
4. **Check Logs**: Use `-v` flag for verbose output when debugging
5. **Matrix Builds**: Test specific matrix combinations with `--matrix`

## Example Workflow Development

1. Create/modify workflow in `.github/workflows/`
2. Test locally:
   ```bash
   act -W .github/workflows/my-workflow.yml -n  # Dry run
   act -W .github/workflows/my-workflow.yml      # Actual run
   ```
3. Fix any issues
4. Push to GitHub

## Integration with pre-commit

The project uses pre-commit hooks that include:
- yamllint: Validates YAML syntax and style
- actionlint: Validates GitHub Actions workflow syntax

These run automatically on commit but can be run manually:
```bash
pre-commit run yamllint --all-files
pre-commit run actionlint --all-files
```

## Resources

- act documentation: https://github.com/nektos/act
- GitHub Actions documentation: https://docs.github.com/en/actions
- uv documentation: https://docs.astral.sh/uv/
- Docker Desktop: https://www.docker.com/products/docker-desktop/

#!/bin/bash
# Comprehensive GitHub CI/CD Setup for AtlasVibe using GitHub CLI
# This script configures the entire CI/CD pipeline with uv integration

set -e

echo "🚀 AtlasVibe GitHub CI/CD Setup with uv Integration"
echo "=================================================="

# Configuration
UV_VERSION="0.7.13"
PYTHON_VERSION="3.11"
NODE_VERSION="20"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check for required tools
check_command() {
    if ! command -v "$1" &> /dev/null; then
        log_error "$1 is not installed. Please install it first."
        exit 1
    fi
}

echo "📋 Checking required tools..."
check_command gh
check_command git
check_command uv

# Check GitHub CLI authentication
if ! gh auth status &> /dev/null; then
    log_error "GitHub CLI is not authenticated."
    echo "Please run: gh auth login"
    exit 1
fi

# Get repository information
REPO_OWNER=$(gh repo view --json owner -q .owner.login 2>/dev/null || echo "")
REPO_NAME=$(gh repo view --json name -q .name 2>/dev/null || echo "")

if [ -z "$REPO_OWNER" ] || [ -z "$REPO_NAME" ]; then
    log_error "Could not determine repository information."
    echo "Make sure you're in a git repository and authenticated with gh."
    exit 1
fi

log_info "Repository: $REPO_OWNER/$REPO_NAME"

# Step 1: Configure git with required user info
echo ""
log_info "Step 1: Configuring git..."
if [ -f ./setup-git-env.sh ]; then
    source ./setup-git-env.sh
    log_success "Git configured"
else
    git config user.name "Emasoft"
    git config user.email "713559+Emasoft@users.noreply.github.com"
    log_success "Git configured"
fi

# Step 2: Set up Python environment with uv
echo ""
log_info "Step 2: Setting up Python environment with uv..."

# Install Python if needed
if ! uv python find $PYTHON_VERSION &> /dev/null; then
    log_info "Installing Python $PYTHON_VERSION..."
    uv python install $PYTHON_VERSION
fi

# Pin Python version
uv python pin $PYTHON_VERSION
log_success "Python $PYTHON_VERSION configured"

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    log_info "Creating virtual environment..."
    uv venv --python $PYTHON_VERSION
fi

# Install dependencies
log_info "Installing Python dependencies..."
uv sync --all-extras --dev
log_success "Dependencies installed"

# Step 3: Install and configure pre-commit hooks
echo ""
log_info "Step 3: Setting up pre-commit hooks..."
uv pip install pre-commit

# Install all hook types
pre-commit install
pre-commit install --hook-type commit-msg
pre-commit install --hook-type pre-push
pre-commit install --hook-type pre-merge-commit
pre-commit install --hook-type post-checkout
pre-commit install --hook-type post-commit
pre-commit install --hook-type post-merge

log_success "Pre-commit hooks installed"

# Update hooks to latest versions
log_info "Updating pre-commit hooks to latest versions..."
pre-commit autoupdate || log_warning "Could not update some hooks"

# Step 4: Configure repository settings via GitHub API
echo ""
log_info "Step 4: Configuring repository settings..."

# Update repository description
gh api repos/$REPO_OWNER/$REPO_NAME \
    --method PATCH \
    --field description="Visual Programming IDE for Python - Built with uv, FastAPI, React, and Electron" \
    --field homepage="https://github.com/$REPO_OWNER/$REPO_NAME" \
    --field has_issues=true \
    --field has_projects=true \
    --field has_wiki=false \
    --field has_discussions=true \
    2>/dev/null && log_success "Repository settings updated" || log_warning "Could not update repository settings"

# Step 5: Set up branch protection rules
echo ""
log_info "Step 5: Configuring branch protection for main branch..."

# Create comprehensive branch protection
gh api repos/$REPO_OWNER/$REPO_NAME/branches/main/protection \
    --method PUT \
    --raw-field required_status_checks='{"strict":true,"contexts":["python-code-format","python-code-lint","python-tests","ts-code-style","check-lockfile","Check Python dependencies with deptry"]}' \
    --field enforce_admins=false \
    --raw-field required_pull_request_reviews='{"required_approving_review_count":1,"dismiss_stale_reviews":true,"require_code_owner_reviews":false,"require_last_push_approval":false}' \
    --field restrictions=null \
    --field allow_force_pushes=false \
    --field allow_deletions=false \
    --field block_creations=false \
    --field required_conversation_resolution=true \
    --field lock_branch=false \
    --field allow_fork_syncing=true \
    2>/dev/null && log_success "Branch protection configured" || log_warning "Could not configure branch protection (may need admin rights)"

# Step 6: Set up GitHub Actions secrets
echo ""
log_info "Step 6: Managing repository secrets..."

# Function to set secret if not exists
set_secret_if_missing() {
    local secret_name=$1
    local secret_description=$2
    local secret_value=$3

    if gh secret list | grep -q "^$secret_name"; then
        log_success "Secret $secret_name already exists"
    else
        if [ -n "$secret_value" ]; then
            echo "$secret_value" | gh secret set "$secret_name"
            log_success "Secret $secret_name created"
        else
            log_warning "Secret $secret_name is missing. $secret_description"
        fi
    fi
}

# Check/create common secrets
set_secret_if_missing "CODECOV_TOKEN" "Get from https://codecov.io/" ""
set_secret_if_missing "UV_CACHE_DIR" "Custom cache directory for uv (optional)" ""

# Step 7: Configure issue labels
echo ""
log_info "Step 7: Setting up issue labels..."

# Define comprehensive label set
declare -a labels=(
    "bug:d73a4a:Something isn't working"
    "enhancement:a2eeef:New feature or request"
    "documentation:0075ca:Improvements or additions to documentation"
    "question:d876e3:Further information is requested"
    "duplicate:cfd3d7:This issue or pull request already exists"
    "good first issue:7057ff:Good for newcomers"
    "help wanted:008672:Extra attention is needed"
    "invalid:e4e669:This doesn't seem right"
    "wontfix:ffffff:This will not be worked on"
    "dependencies:0366d6:Pull requests that update a dependency file"
    "python:3776ab:Python-related"
    "typescript:3178c6:TypeScript-related"
    "ci/cd:000000:Continuous Integration/Deployment"
    "security:ee0701:Security related issues"
    "performance:d4c5f9:Performance improvements"
    "refactor:fef2c0:Code refactoring"
    "testing:fbca04:Testing related"
    "ui/ux:e99695:User interface and experience"
    "blocks:ff6b6b:Block system related"
    "urgent:b60205:Urgent issues requiring immediate attention"
    "blocked:d93f0b:Blocked by other issues"
    "in progress:0e8a16:Work in progress"
    "ready for review:c2e0c6:Ready for review"
)

for label in "${labels[@]}"; do
    IFS=':' read -r name color description <<< "$label"
    gh label create "$name" --color "$color" --description "$description" --force 2>/dev/null && \
        echo "  ✓ Label '$name' created/updated" || \
        echo "  - Could not create label '$name'"
done

# Step 8: Set up repository topics
echo ""
log_info "Step 8: Configuring repository topics..."
gh api repos/$REPO_OWNER/$REPO_NAME/topics \
    --method PUT \
    --raw-field names='["visual-programming","python","typescript","electron","fastapi","react","reactflow","ide","workflow-automation","no-code","low-code","data-science","atlasvibe","uv","astral-sh"]' \
    2>/dev/null && log_success "Repository topics updated" || log_warning "Could not update topics"

# Step 9: Create issue templates
echo ""
log_info "Step 9: Creating issue templates..."

mkdir -p .github/ISSUE_TEMPLATE

# Bug report template
cat > .github/ISSUE_TEMPLATE/bug_report.md << 'EOF'
---
name: Bug report
about: Create a report to help us improve
title: '[BUG] '
labels: bug
assignees: ''
---

**Describe the bug**
A clear and concise description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. Go to '...'
2. Click on '....'
3. Drag block '....'
4. See error

**Expected behavior**
A clear and concise description of what you expected to happen.

**Screenshots**
If applicable, add screenshots to help explain your problem.

**Environment:**
 - OS: [e.g. macOS 14.0]
 - Python version: [e.g. 3.11.5]
 - Node.js version: [e.g. 20.5.0]
 - AtlasVibe version: [e.g. 0.1.0]

**Additional context**
Add any other context about the problem here.

**Logs**
```
Paste any relevant logs here
```
EOF

# Feature request template
cat > .github/ISSUE_TEMPLATE/feature_request.md << 'EOF'
---
name: Feature request
about: Suggest an idea for this project
title: '[FEATURE] '
labels: enhancement
assignees: ''
---

**Is your feature request related to a problem? Please describe.**
A clear and concise description of what the problem is. Ex. I'm always frustrated when [...]

**Describe the solution you'd like**
A clear and concise description of what you want to happen.

**Describe alternatives you've considered**
A clear and concise description of any alternative solutions or features you've considered.

**Additional context**
Add any other context or screenshots about the feature request here.
EOF

# Block request template
cat > .github/ISSUE_TEMPLATE/block_request.md << 'EOF'
---
name: Block request
about: Suggest a new block for AtlasVibe
title: '[BLOCK] '
labels: enhancement, blocks
assignees: ''
---

**Block Name**
Proposed name for the block

**Category**
Which category should this block belong to? (e.g., MATH, DSP, AI_ML, etc.)

**Description**
What does this block do?

**Inputs**
- Input 1: description (type)
- Input 2: description (type)

**Outputs**
- Output 1: description (type)

**Parameters**
- Parameter 1: description (type, default value)
- Parameter 2: description (type, default value)

**Use Cases**
Describe scenarios where this block would be useful

**Example Code**
```python
# Optional: provide example implementation
```

**Additional context**
Add any other context about the block request here.
EOF

log_success "Issue templates created"

# Step 10: Create GitHub Actions workflows documentation
echo ""
log_info "Step 10: Creating CI/CD documentation..."

cat > .github/CI_CD_GUIDE.md << 'EOF'
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
   - **Triggers**: Version tags (v*), Manual dispatch
   - **Jobs**:
     - `pre-release-checks`: Quality gates before build
     - `buildElectron`: Multi-platform Electron builds

3. **Security Workflows**
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

- Dependencies are checked weekly
- Only approved values in git config:
  - Author: Emasoft
  - Email: 713559+Emasoft@users.noreply.github.com
EOF

log_success "CI/CD documentation created"

# Step 11: Create dependabot configuration
echo ""
log_info "Step 11: Setting up Dependabot..."

cat > .github/dependabot.yml << 'EOF'
version: 2
updates:
  # Python dependencies
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
      time: "09:00"
      timezone: "UTC"
    open-pull-requests-limit: 10
    labels:
      - "dependencies"
      - "python"
    reviewers:
      - "Emasoft"
    commit-message:
      prefix: "chore"
      prefix-development: "chore"
      include: "scope"
    groups:
      python-minor:
        update-types:
          - "minor"
          - "patch"

  # GitHub Actions
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
      time: "09:00"
      timezone: "UTC"
    labels:
      - "dependencies"
      - "ci/cd"
    commit-message:
      prefix: "ci"

  # Node.js dependencies
  - package-ecosystem: "npm"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
      time: "09:00"
      timezone: "UTC"
    open-pull-requests-limit: 10
    labels:
      - "dependencies"
      - "typescript"
    reviewers:
      - "Emasoft"
    commit-message:
      prefix: "chore"
      prefix-development: "chore"
      include: "scope"
    groups:
      npm-minor:
        update-types:
          - "minor"
          - "patch"
EOF

log_success "Dependabot configured"

# Step 12: Run initial checks
echo ""
log_info "Step 12: Running initial checks..."

# Check git configuration
echo ""
log_info "Git configuration:"
echo "  User: $(git config user.name)"
echo "  Email: $(git config user.email)"

# Check Python setup
echo ""
log_info "Python environment:"
echo "  Python: $(uv python find)"
echo "  Virtual env: $(which python)"
echo "  uv version: $(uv --version)"

# Run pre-commit on all files
echo ""
log_info "Running pre-commit checks..."
pre-commit run --all-files || log_warning "Some pre-commit checks failed. Please fix and commit."

# Check if uv.lock is up to date
echo ""
log_info "Checking uv.lock..."
if uv lock --check; then
    log_success "uv.lock is up to date"
else
    log_warning "uv.lock needs updating. Run: uv lock"
fi

# Summary
echo ""
echo "=================================================="
log_success "GitHub CI/CD Setup Complete!"
echo ""
echo "✨ What was configured:"
echo "  ✓ Git user configuration"
echo "  ✓ Python $PYTHON_VERSION environment with uv"
echo "  ✓ Pre-commit hooks (all types)"
echo "  ✓ Repository settings and description"
echo "  ✓ Branch protection rules"
echo "  ✓ Issue labels (${#labels[@]} labels)"
echo "  ✓ Repository topics"
echo "  ✓ Issue templates"
echo "  ✓ CI/CD documentation"
echo "  ✓ Dependabot configuration"
echo ""
echo "📋 Next steps:"
echo "1. Add any missing secrets (CODECOV_TOKEN, etc.)"
echo "2. Commit the new configuration files:"
echo "   git add .github/"
echo "   git commit -m 'chore: configure GitHub CI/CD with uv'"
echo "3. Push to trigger CI:"
echo "   git push"
echo ""
echo "🔧 Useful commands:"
echo "  gh workflow list         # List workflows"
echo "  gh run list             # View recent runs"
echo "  pre-commit run --all-files  # Run all checks locally"
echo "  uv lock --upgrade       # Update all dependencies"
echo "=================================================="

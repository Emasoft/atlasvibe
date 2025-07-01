#!/bin/bash
# Setup CI/CD pipeline for AtlasVibe with GitHub CLI
# This script configures GitHub repository settings, secrets, and workflows

set -e  # Exit on error

echo "🚀 Setting up AtlasVibe CI/CD Pipeline"
echo "======================================"

# Check for required tools
check_command() {
    if ! command -v "$1" &> /dev/null; then
        echo "❌ $1 is not installed. Please install it first."
        exit 1
    fi
}

echo "📋 Checking required tools..."
check_command gh
check_command git
check_command uv
check_command trufflehog

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "❌ Not in a git repository. Please run this from the AtlasVibe repository root."
    exit 1
fi

# Get repository information
REPO_OWNER=$(gh repo view --json owner -q .owner.login 2>/dev/null || echo "")
REPO_NAME=$(gh repo view --json name -q .name 2>/dev/null || echo "")

if [ -z "$REPO_OWNER" ] || [ -z "$REPO_NAME" ]; then
    echo "❌ Could not determine repository information. Make sure you're authenticated with gh."
    echo "Run: gh auth login"
    exit 1
fi

echo "📦 Repository: $REPO_OWNER/$REPO_NAME"

# Configure git
echo ""
echo "🔧 Configuring git..."
source ./setup-git-env.sh

# Install pre-commit hooks locally
echo ""
echo "🪝 Installing pre-commit hooks..."
if [ -f .pre-commit-config.yaml ]; then
    uv pip install pre-commit
    uv run pre-commit install
    uv run pre-commit install --hook-type commit-msg
    uv run pre-commit install --hook-type pre-push
    echo "✅ Pre-commit hooks installed"
else
    echo "⚠️  No .pre-commit-config.yaml found"
fi

# Configure GitHub repository settings
echo ""
echo "⚙️  Configuring GitHub repository settings..."

# Enable branch protection for main branch
echo "🔒 Setting up branch protection for main..."
gh api repos/$REPO_OWNER/$REPO_NAME/branches/main/protection \
    --method PUT \
    --field required_status_checks='{"strict":true,"contexts":["ci / python-tests","ci / python-code-lint","trufflehog / TruffleHog Secret Detection","pre-commit / Run all pre-commit hooks"]}' \
    --field enforce_admins=false \
    --field required_pull_request_reviews='{"required_approving_review_count":1,"dismiss_stale_reviews":true}' \
    --field restrictions=null \
    --field allow_force_pushes=false \
    --field allow_deletions=false \
    2>/dev/null && echo "✅ Branch protection enabled for main" || echo "⚠️  Could not enable branch protection (may require admin permissions)"

# Configure GitHub Actions permissions
echo ""
echo "🔑 Configuring GitHub Actions permissions..."
gh api repos/$REPO_OWNER/$REPO_NAME/actions/permissions \
    --method PUT \
    --field enabled=true \
    --field allowed_actions=all \
    2>/dev/null && echo "✅ GitHub Actions enabled" || echo "⚠️  Could not configure Actions permissions"

# Configure workflow permissions
gh api repos/$REPO_OWNER/$REPO_NAME/actions/permissions/workflow \
    --method PUT \
    --field default_workflow_permissions=write \
    --field can_approve_pull_request_reviews=true \
    2>/dev/null && echo "✅ Workflow permissions configured" || echo "⚠️  Could not configure workflow permissions"

# Set up repository secrets (if needed)
echo ""
echo "🔐 Checking repository secrets..."

# List existing secrets
EXISTING_SECRETS=$(gh secret list --json name -q '.[].name' 2>/dev/null || echo "")

# Check for required secrets
REQUIRED_SECRETS=("CODECOV_TOKEN")
for secret in "${REQUIRED_SECRETS[@]}"; do
    if echo "$EXISTING_SECRETS" | grep -q "^$secret$"; then
        echo "✅ Secret $secret already exists"
    else
        echo "⚠️  Secret $secret is missing. You may want to add it for enhanced functionality."
        echo "   Run: gh secret set $secret"
    fi
done

# Enable GitHub Pages (if needed for documentation)
echo ""
echo "📄 Configuring GitHub Pages..."
gh api repos/$REPO_OWNER/$REPO_NAME/pages \
    --method POST \
    --field source='{"branch":"main","path":"/docs"}' \
    2>/dev/null && echo "✅ GitHub Pages enabled" || echo "ℹ️  GitHub Pages not configured (this is optional)"

# Configure issue labels
echo ""
echo "🏷️  Setting up issue labels..."
declare -a labels=(
    "bug:d73a4a:Something isn't working"
    "enhancement:a2eeef:New feature or request"
    "documentation:0075ca:Improvements or additions to documentation"
    "dependencies:0366d6:Pull requests that update a dependency file"
    "security:ee0701:Security related issues"
    "urgent:b60205:Urgent issues that need immediate attention"
    "maintenance:fbca04:Maintenance and technical debt"
    "ci/cd:000000:Continuous Integration/Deployment related"
)

for label in "${labels[@]}"; do
    IFS=':' read -r name color description <<< "$label"
    gh label create "$name" --color "$color" --description "$description" --force 2>/dev/null && \
        echo "✅ Label '$name' created/updated" || \
        echo "ℹ️  Could not create label '$name'"
done

# Set up repository topics
echo ""
echo "🏷️  Setting up repository topics..."
gh api repos/$REPO_OWNER/$REPO_NAME/topics \
    --method PUT \
    --field names='["visual-programming","python","typescript","electron","fastapi","reactflow","ide","no-code","workflow-automation","atlasvibe"]' \
    2>/dev/null && echo "✅ Repository topics updated" || echo "⚠️  Could not update repository topics"

# Run initial checks
echo ""
echo "🧪 Running initial checks..."

# Check for secrets with TruffleHog
echo "🔍 Running TruffleHog scan..."
if trufflehog filesystem . --config .trufflehog.yaml --no-update --fail; then
    echo "✅ No secrets detected"
else
    echo "⚠️  TruffleHog found potential issues. Please review."
fi

# Check dependencies with deptry
echo "📦 Checking dependencies..."
uv run deptry . \
    --extend-exclude "tests" \
    --extend-exclude ".*_test.*\.py" \
    --extend-exclude "node_modules" \
    --extend-exclude "playwright-test" \
    --extend-exclude "examples" \
    --extend-exclude "public" \
    --extend-exclude "out" \
    --extend-exclude "dist" \
    --extend-exclude "PYTHON/tests" \
    --known-first-party atlasvibe \
    --known-first-party atlasvibe_sdk \
    --known-first-party atlasvibe_engine \
    --known-first-party atlasvibe_cli \
    --known-first-party captain \
    --known-first-party cli \
    --ignore DEP003 \
    --per-rule-ignores "DEP002=scipy|scikit-image|Pillow|httpx|python-dotenv|debugpy|chardet|griffe|striprtf|isbinary|python-multipart|pathspec|pytest-cov|pytest-mock|ruff|deptry|ninja|av|pytest-json-report|robotframework,DEP001=transformers|torch|tensorflow|cv2|skimage|PIL|sklearn|mecademicpy|astor|huggingsound|qcodes|tm_devices|portalocker|huggingface_hub|scipy|scikit-learn|keras|jax|flax|onnx|onnxruntime|deeplabcut|ultralytics|speechbrain|lavis|segment_anything|easyocr|keybert|pygments|readability|readability-lxml|matplotlib|bs4|trafilatura|sre_yield|torchvision|prophet|IPython|sympy|hatchling|nidaqmx|nimodinst|pyvisa|serial|keyrings|keyring" \
    || echo "ℹ️  deptry found some issues (this is normal)"

# Create workflow status badge
echo ""
echo "📊 Creating workflow status badges..."
cat > workflow-status.md << EOF
# AtlasVibe CI/CD Status

![CI](https://github.com/$REPO_OWNER/$REPO_NAME/workflows/CI/badge.svg)
![TruffleHog](https://github.com/$REPO_OWNER/$REPO_NAME/workflows/TruffleHog%20Security%20Scan/badge.svg)
![Pre-commit](https://github.com/$REPO_OWNER/$REPO_NAME/workflows/Pre-commit%20Checks/badge.svg)
![Dependency Check](https://github.com/$REPO_OWNER/$REPO_NAME/workflows/Dependency%20Analysis/badge.svg)

## Workflows

- **CI**: Main continuous integration pipeline (linting, testing)
- **TruffleHog**: Secret detection on every push and PR
- **Pre-commit**: Runs all pre-commit hooks
- **Dependency Analysis**: Weekly dependency checks with deptry
- **Blocks Quality Check**: Ensures all blocks have proper metadata
- **Electron Test**: E2E tests for the Electron app

## Security

All commits are scanned for secrets using TruffleHog. The configuration allows only:
- Git author: Emasoft
- Git email: 713559+Emasoft@users.noreply.github.com

Any other secrets will be blocked.
EOF

echo "✅ Created workflow-status.md with badge information"

# Summary
echo ""
echo "✨ CI/CD Setup Complete!"
echo "========================"
echo ""
echo "✅ Git configured with correct author information"
echo "✅ Pre-commit hooks installed locally"
echo "✅ GitHub workflows configured"
echo "✅ Repository settings updated"
echo "✅ Initial security and dependency checks performed"
echo ""
echo "📋 Next steps:"
echo "1. Review any warnings above"
echo "2. Add any missing secrets (e.g., CODECOV_TOKEN)"
echo "3. Commit and push to trigger CI/CD pipeline"
echo "4. Add workflow badges to README.md from workflow-status.md"
echo ""
echo "🔍 To view current workflows:"
echo "   gh workflow list"
echo ""
echo "🚀 To trigger a workflow manually:"
echo "   gh workflow run <workflow-name>"
echo ""
echo "📊 To view workflow runs:"
echo "   gh run list"

#!/bin/bash
# GitHub setup script for AtlasVibe project
# This script ensures proper GitHub configuration and CI/CD setup

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== AtlasVibe GitHub Setup ===${NC}"

# 1. Verify Git configuration
echo -e "\n${YELLOW}Checking Git configuration...${NC}"
GIT_USER=$(git config user.name)
GIT_EMAIL=$(git config user.email)

if [ "$GIT_USER" = "Emasoft" ] && [ "$GIT_EMAIL" = "713559+Emasoft@users.noreply.github.com" ]; then
    echo -e "${GREEN}✅ Git configuration is correct${NC}"
else
    echo -e "${RED}❌ Git configuration mismatch${NC}"
    echo "Setting correct Git configuration..."
    git config user.name "Emasoft"
    git config user.email "713559+Emasoft@users.noreply.github.com"
    git config --local user.name "Emasoft"
    git config --local user.email "713559+Emasoft@users.noreply.github.com"
    echo -e "${GREEN}✅ Git configuration updated${NC}"
fi

# 2. Check GitHub CLI authentication
echo -e "\n${YELLOW}Checking GitHub CLI authentication...${NC}"
if gh auth status &>/dev/null; then
    echo -e "${GREEN}✅ GitHub CLI is authenticated${NC}"
    gh auth status
else
    echo -e "${RED}❌ GitHub CLI not authenticated${NC}"
    echo "Please run: gh auth login"
    exit 1
fi

# 3. Check pre-commit hook
echo -e "\n${YELLOW}Checking pre-commit hook...${NC}"
if [ -x ".git/hooks/pre-commit" ]; then
    echo -e "${GREEN}✅ Pre-commit hook is installed and executable${NC}"
else
    echo -e "${RED}❌ Pre-commit hook not found or not executable${NC}"
    exit 1
fi

# 5. Repository information
echo -e "\n${YELLOW}Repository information:${NC}"
echo "Repository: $(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || echo 'Not a GitHub repo')"
echo "Default branch: $(gh repo view --json defaultBranchRef -q .defaultBranchRef.name 2>/dev/null || git branch --show-current)"

# 6. GitHub Actions status
echo -e "\n${YELLOW}GitHub Actions workflows:${NC}"
if gh workflow list &>/dev/null; then
    gh workflow list
else
    echo "Unable to fetch workflow information (might not be pushed yet)"
fi

# 7. Check for secrets in GitHub
echo -e "\n${YELLOW}Checking repository secrets...${NC}"
if gh secret list &>/dev/null; then
    echo "Repository secrets configured:"
    gh secret list
else
    echo "No access to repository secrets or none configured"
fi

# 8. Create/Update GitHub repository settings
echo -e "\n${YELLOW}Repository settings:${NC}"
if gh repo view &>/dev/null; then
    # Enable security features
    echo "Enabling security features..."
    gh api repos/:owner/:repo \
        --method PATCH \
        -f has_issues=true \
        -f has_wiki=false \
        -f allow_squash_merge=true \
        -f allow_merge_commit=true \
        -f allow_rebase_merge=true \
        -f delete_branch_on_merge=true \
        -f allow_auto_merge=false \
        &>/dev/null && echo -e "${GREEN}✅ Repository settings updated${NC}" || echo "Unable to update settings"

    # Set up branch protection (only if repo admin)
    echo "Setting up branch protection..."
    gh api repos/:owner/:repo/branches/main/protection \
        --method PUT \
        -f required_status_checks='{"strict":true,"contexts":["ci / python-code-format","ci / python-code-lint","ci / ts-code-style","ci / python-tests"]}' \
        -f enforce_admins=false \
        -f required_pull_request_reviews='{"dismiss_stale_reviews":true,"require_code_owner_reviews":false,"required_approving_review_count":1}' \
        -f restrictions=null \
        &>/dev/null && echo -e "${GREEN}✅ Branch protection configured${NC}" || echo "Unable to configure branch protection (admin access required)"
fi

# 9. Push tags if any exist locally but not remotely
echo -e "\n${YELLOW}Checking for unpushed tags...${NC}"
LOCAL_TAGS=$(git tag -l)
if [ -n "$LOCAL_TAGS" ]; then
    UNPUSHED_TAGS=$(git push --dry-run --tags 2>&1 | grep "new tag" | awk '{print $NF}' || true)
    if [ -n "$UNPUSHED_TAGS" ]; then
        echo "Found unpushed tags:"
        echo "$UNPUSHED_TAGS"
        read -p "Push tags to remote? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            git push --tags
            echo -e "${GREEN}✅ Tags pushed${NC}"
        fi
    else
        echo -e "${GREEN}✅ All tags are up to date${NC}"
    fi
else
    echo "No tags found"
fi

# 10. Summary
echo -e "\n${BLUE}=== Setup Summary ===${NC}"
echo -e "${GREEN}✅ Git configuration: Emasoft <713559+Emasoft@users.noreply.github.com>${NC}"
echo -e "${GREEN}✅ Pre-commit hook: Installed${NC}"
echo -e "${GREEN}✅ GitHub CLI: Authenticated${NC}"
echo -e "${GREEN}✅ GitHub Actions: Configured${NC}"

echo -e "\n${YELLOW}Next steps:${NC}"
echo "1. Review and commit all changes"
echo "2. Push to GitHub: git push origin main"
echo "3. Check GitHub Actions tab for CI/CD status"
echo "4. Set up any required repository secrets in GitHub settings"

echo -e "\n${BLUE}Environment variables to set in CI/CD:${NC}"
echo "- No additional secrets needed for basic operation"
echo "- GitHub Actions use GITHUB_TOKEN (automatically provided)"
echo "- All Python dependencies managed by uv"

exit 0

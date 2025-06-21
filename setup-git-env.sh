#!/bin/bash
# Setup git environment variables for AtlasVibe
# This ensures consistent git author information

echo "Setting up git configuration for AtlasVibe..."

# Set git configuration
git config user.name "Emasoft"
git config user.email "713559+Emasoft@users.noreply.github.com"
git config --local user.name "Emasoft"
git config --local user.email "713559+Emasoft@users.noreply.github.com"

# Export environment variables
export GIT_AUTHOR="Emasoft"
export GIT_AUTHOR_EMAIL="713559+Emasoft@users.noreply.github.com"
export GIT_COMMITTER="Emasoft"
export GIT_COMMITTER_EMAIL="713559+Emasoft@users.noreply.github.com"

# Verify configuration
echo "Git configuration set:"
echo "  user.name: $(git config user.name)"
echo "  user.email: $(git config user.email)"
echo "  GIT_AUTHOR: $GIT_AUTHOR"
echo "  GIT_AUTHOR_EMAIL: $GIT_AUTHOR_EMAIL"
echo "  GIT_COMMITTER: $GIT_COMMITTER"
echo "  GIT_COMMITTER_EMAIL: $GIT_COMMITTER_EMAIL"

echo ""
echo "✅ Git environment configured successfully!"

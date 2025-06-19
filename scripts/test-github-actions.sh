#!/bin/bash
# Script to test GitHub Actions locally using act with uv support

set -e

echo "🎭 Testing GitHub Actions locally with act..."
echo "================================================"

# Check if act is installed
if ! command -v act &> /dev/null; then
    echo "❌ Error: act is not installed. Please install it with: brew install act"
    exit 1
fi

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo "❌ Error: Docker is not running. Please start Docker Desktop."
    exit 1
fi

# Function to run a specific workflow
run_workflow() {
    local workflow=$1
    local job=$2

    echo ""
    echo "🚀 Running workflow: $workflow"
    if [ -n "$job" ]; then
        echo "   Job: $job"
        act -W ".github/workflows/$workflow" -j "$job" --container-architecture linux/amd64
    else
        echo "   All jobs"
        act -W ".github/workflows/$workflow" --container-architecture linux/amd64
    fi
}

# Parse command line arguments
case "$1" in
    "ci")
        run_workflow "ci.yml" "$2"
        ;;
    "pre-commit")
        run_workflow "pre-commit.yml" "$2"
        ;;
    "dependency-check")
        run_workflow "dependency-check.yml" "$2"
        ;;
    "gitleaks")
        run_workflow "gitleaks.yml" "$2"
        ;;
    "cd")
        echo "⚠️  Warning: CD workflow requires secrets. Use --secret-file .env.secrets"
        run_workflow "cd.yaml" "$2"
        ;;
    "list")
        echo "📋 Available workflows:"
        act -l
        ;;
    "")
        echo "Usage: $0 <workflow> [job]"
        echo ""
        echo "Available workflows:"
        echo "  ci              - Main CI pipeline"
        echo "  pre-commit      - Pre-commit checks"
        echo "  dependency-check - Dependency analysis"
        echo "  gitleaks        - Secret scanning"
        echo "  cd              - Continuous deployment (requires secrets)"
        echo "  list            - List all available workflows and jobs"
        echo ""
        echo "Examples:"
        echo "  $0 ci                    # Run all CI jobs"
        echo "  $0 ci python-tests       # Run only python-tests job"
        echo "  $0 pre-commit            # Run pre-commit checks"
        echo "  $0 list                  # List all workflows"
        ;;
    *)
        echo "❌ Unknown workflow: $1"
        echo "Run '$0' without arguments to see usage."
        exit 1
        ;;
esac

echo ""
echo "✅ Done!"

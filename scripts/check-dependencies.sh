#!/bin/bash
# Script to check Python dependencies with deptry
# This script provides a consistent way to run deptry with AtlasVibe-specific configuration

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== AtlasVibe Dependency Check ===${NC}"

# Check if uv is available
if ! command -v uv &> /dev/null; then
    echo -e "${RED}❌ uv is not installed${NC}"
    echo "Please install uv: https://github.com/astral-sh/uv"
    exit 1
fi

# Common exclusions for AtlasVibe
EXCLUDE_PATTERNS=(
    "tests"
    ".*_test.*\.py"
    "node_modules"
    "playwright-test"
    "examples"
    "public"
    "out"
    "dist"
    "PYTHON/tests"
)

# First-party modules
FIRST_PARTY=(
    "atlasvibe"
    "atlasvibe_sdk"
    "atlasvibe_engine"
    "atlasvibe_cli"
    "captain"
    "cli"
)

# Dependencies to ignore for DEP002 (unused)
# These are used by blocks or optional features
DEP002_IGNORE=(
    "scipy"
    "scikit-image"
    "Pillow"
    "httpx"
    "python-dotenv"
    "debugpy"
    "chardet"
    "griffe"
    "striprtf"
    "isbinary"
    "python-multipart"
    "pathspec"
    "pytest-cov"
    "pytest-mock"
    "ruff"
    "deptry"
)

# Dependencies to ignore for DEP001 (missing)
# These are imported dynamically by blocks
DEP001_IGNORE=(
    "transformers"
    "torch"
    "tensorflow"
    "cv2"
    "skimage"
    "PIL"
    "sklearn"
    "mecademicpy"
    "astor"
    "huggingsound"
    "qcodes"
    "tm_devices"
    "portalocker"
    "huggingface_hub"
    "scipy"
    "scikit-learn"
    "keras"
    "jax"
    "flax"
    "onnx"
    "onnxruntime"
    "deeplabcut"
    "ultralytics"
    "speechbrain"
    "lavis"
    "segment_anything"
    "easyocr"
    "keybert"
    "pygments"
    "readability"
    "readability-lxml"
    "matplotlib"
    "bs4"
    "trafilatura"
    "sre_yield"
)

# Build command arguments
CMD="uv run deptry ."

# Add exclusions
for pattern in "${EXCLUDE_PATTERNS[@]}"; do
    CMD="$CMD --extend-exclude \"$pattern\""
done

# Add first-party modules
for module in "${FIRST_PARTY[@]}"; do
    CMD="$CMD --known-first-party $module"
done

# Always ignore DEP003 (transitive dependencies)
CMD="$CMD --ignore DEP003"

# Build per-rule-ignores string
PER_RULE_IGNORES="DEP002=$(IFS='|'; echo "${DEP002_IGNORE[*]}"),DEP001=$(IFS='|'; echo "${DEP001_IGNORE[*]}")"
CMD="$CMD --per-rule-ignores \"$PER_RULE_IGNORES\""

# Add optional flags
if [[ "${1:-}" == "--json" ]]; then
    CMD="$CMD --json-output deptry-report.json"
    echo -e "${YELLOW}JSON output will be saved to deptry-report.json${NC}"
elif [[ "${1:-}" == "--verbose" ]]; then
    CMD="$CMD --verbose"
fi

# Run deptry
echo -e "${YELLOW}Running deptry...${NC}"
echo -e "${BLUE}Command: $CMD${NC}\n"

if eval $CMD; then
    echo -e "\n${GREEN}✅ No dependency issues found!${NC}"
    exit 0
else
    EXIT_CODE=$?
    echo -e "\n${YELLOW}⚠️  deptry found some issues${NC}"
    echo -e "${YELLOW}Many of these might be false positives due to:${NC}"
    echo "- Dynamic imports in blocks"
    echo "- Optional dependencies for specific features"
    echo "- Development tools used indirectly"
    echo ""
    echo -e "${BLUE}To add exceptions:${NC}"
    echo "1. Edit this script to add packages to DEP001_IGNORE or DEP002_IGNORE"
    echo "2. Update .git/hooks/pre-commit with the same ignores"
    echo "3. Update .github/workflows/dependency-check.yml"
    exit $EXIT_CODE
fi

#!/bin/bash
# Check if block metadata is synchronized

set -e

# Run sync command
uv run python -m cli.cmd.sync

# Check if there are any changes to block files
if ! git diff --exit-code --quiet blocks/; then
    echo "Error: Block metadata is out of sync!"
    echo "Please run: uv run python -m cli.cmd.sync"
    echo ""
    echo "Changed files:"
    git diff --name-only blocks/
    exit 1
fi

echo "Block metadata is synchronized."
exit 0

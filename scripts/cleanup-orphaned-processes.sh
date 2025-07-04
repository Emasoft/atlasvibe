#!/usr/bin/env bash
# Cleanup script for orphaned pre-commit processes
# This script finds and kills any pre-commit processes that have been orphaned

set -euo pipefail

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== Orphaned Process Cleanup ===${NC}"
echo "Scanning for orphaned pre-commit processes..."

# Find all pre-commit-wrapper-robust processes
ORPHANED_COUNT=0
CLEANED_COUNT=0

# Function to check if a process is orphaned
is_orphaned() {
    local pid=$1
    local ppid=$(ps -p "$pid" -o ppid= 2>/dev/null | tr -d ' ')

    # Process is orphaned if parent is init (1) or doesn't exist
    if [ -z "$ppid" ] || [ "$ppid" = "1" ]; then
        return 0
    fi
    return 1
}

# Find all pre-commit wrapper processes
while IFS= read -r line; do
    if [ -z "$line" ]; then
        continue
    fi

    pid=$(echo "$line" | awk '{print $2}')
    cmd=$(echo "$line" | awk '{for(i=11;i<=NF;i++) printf "%s ", $i; print ""}')

    if is_orphaned "$pid"; then
        ORPHANED_COUNT=$((ORPHANED_COUNT + 1))
        echo -e "${RED}Found orphaned process:${NC}"
        echo "  PID: $pid"
        echo "  Command: $cmd"

        # Get process details
        elapsed=$(ps -p "$pid" -o etime= 2>/dev/null | tr -d ' ' || echo "unknown")
        echo "  Running time: $elapsed"

        # Kill the process
        if kill -TERM "$pid" 2>/dev/null; then
            sleep 2
            if kill -0 "$pid" 2>/dev/null; then
                kill -KILL "$pid" 2>/dev/null || true
            fi
            CLEANED_COUNT=$((CLEANED_COUNT + 1))
            echo -e "  ${GREEN}✓ Process killed${NC}"
        else
            echo -e "  ${RED}✗ Failed to kill process${NC}"
        fi
        echo ""
    fi
done < <(ps aux | grep -E "pre-commit-wrapper-robust|\.git/hooks/pre-commit" | grep -v grep | grep -v "cleanup-orphaned")

# Clean up stale PID files
echo "Checking for stale PID files..."
STALE_FILES=0

for pidfile in /tmp/pre-commit-*.pid; do
    if [ -f "$pidfile" ]; then
        pid=$(cat "$pidfile" 2>/dev/null || echo "")
        if [ -n "$pid" ] && ! kill -0 "$pid" 2>/dev/null; then
            STALE_FILES=$((STALE_FILES + 1))
            echo -e "${YELLOW}Removing stale PID file:${NC} $pidfile (PID: $pid)"
            rm -f "$pidfile"
        fi
    fi
done

# Clean up old lock files (older than 1 day)
echo "Checking for old lock files..."
OLD_LOCKS=0

find /tmp -name "pre-commit-*.lock" -type f -mtime +1 2>/dev/null | while read -r lockfile; do
    OLD_LOCKS=$((OLD_LOCKS + 1))
    echo -e "${YELLOW}Removing old lock file:${NC} $lockfile"
    rm -f "$lockfile"
done

# Summary
echo ""
echo -e "${GREEN}=== Cleanup Summary ===${NC}"
echo "Orphaned processes found: $ORPHANED_COUNT"
echo "Processes cleaned: $CLEANED_COUNT"
echo "Stale PID files removed: $STALE_FILES"
echo "Old lock files removed: $OLD_LOCKS"

if [ $ORPHANED_COUNT -eq 0 ] && [ $STALE_FILES -eq 0 ]; then
    echo -e "${GREEN}✓ No cleanup needed${NC}"
else
    echo -e "${GREEN}✓ Cleanup completed${NC}"
fi

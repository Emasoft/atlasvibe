#!/usr/bin/env bash
# Memory-limited hook wrapper for resource-intensive tools

set -euo pipefail

# Source constants
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
source "${REPO_ROOT}/.sequential-precommit-constants.sh" 2>/dev/null || true

# Configuration
HOOK_NAME="${1:-unknown}"
shift
MEMORY_LIMIT_MB="${MEMORY_LIMIT_MB:-512}"
TIMEOUT="${HOOK_TIMEOUT:-60}"

# Platform-specific memory limiting
limit_memory() {
    case "$(detect_platform)" in
        linux)
            # Use cgroups v2 if available
            if [ -d "/sys/fs/cgroup/memory" ]; then
                # Try systemd-run if available
                if command -v systemd-run >/dev/null 2>&1; then
                    exec systemd-run --scope -p MemoryLimit="${MEMORY_LIMIT_MB}M" "$@"
                fi
            fi
            # Fall back to ulimit
            ulimit -v $((MEMORY_LIMIT_MB * 1024)) 2>/dev/null || true
            ;;
        macos)
            # macOS doesn't support memory limits via ulimit -v
            # Use ulimit -m for resident set size
            ulimit -m $((MEMORY_LIMIT_MB * 1024)) 2>/dev/null || true
            ;;
    esac
}

# Apply limits
limit_memory

# Run hook with timeout
exec timeout "$TIMEOUT" "$@"

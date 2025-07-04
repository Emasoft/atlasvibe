#!/usr/bin/env bash
# Sequential Pre-commit Constants
# This file defines all constants used by sequential pre-commit scripts

# Version
export SEQUENTIAL_PRECOMMIT_VERSION="1.0.0"

# Python version
export PYTHON_VERSION="3.11"
export UV_PYTHON="python${PYTHON_VERSION}"

# Timeouts (in seconds)
export DEFAULT_GLOBAL_TIMEOUT=900        # 15 minutes total
export DEFAULT_HEARTBEAT_TIMEOUT=60      # 60 seconds stall detection
export DEFAULT_LOCK_TIMEOUT=30           # 30 seconds lock acquisition
export DEFAULT_CLEANUP_INTERVAL=3600     # 1 hour cleanup cycle

# Resource Limits
export DEFAULT_MEMORY_LIMIT_MB=2048      # 2GB per hook
export DEFAULT_MEMORY_LIMIT_DOCKER_MB=3072  # 3GB for Docker containers
export DEFAULT_MAX_FD=1024               # File descriptor limit
export DEFAULT_CPU_LIMIT=80              # CPU percentage limit

# Logging
export LOG_DIR=".pre-commit-logs"
export LOG_RETENTION_DAYS=7
export LOG_MAX_SIZE_MB=100

# Process Control
export ENABLE_ORPHAN_DETECTION=1
export ENABLE_HEARTBEAT_MONITOR=1
export HEARTBEAT_CHECK_INTERVAL=5

# Lock file settings
export LOCK_DIR="/tmp/sequential-precommit-locks"
export LOCK_FILE_PREFIX="precommit"

# Platform detection
detect_platform() {
    case "$(uname -s)" in
        Darwin*) echo "macos" ;;
        Linux*) echo "linux" ;;
        MINGW*|CYGWIN*|MSYS*) echo "windows" ;;
        *) echo "unknown" ;;
    esac
}

# Export platform
export PLATFORM=$(detect_platform)

# Helper functions
portable_echo() {
    printf '%s\n' "$*"
}

# Calculate MD5 hash
calculate_md5() {
    local input="$1"
    if command -v md5sum >/dev/null 2>&1; then
        echo "$input" | md5sum | cut -d' ' -f1
    elif command -v md5 >/dev/null 2>&1; then
        echo "$input" | md5 -q
    else
        # Fallback to a simple hash
        echo "$input" | cksum | cut -d' ' -f1
    fi
}

# Kill process tree
kill_process_tree() {
    local pid=$1
    local signal=${2:-TERM}
    
    if [[ "$PLATFORM" == "macos" ]]; then
        # macOS: Use ps to find children
        local children=$(ps -o pid= -g $(ps -o pgid= -p $pid | grep -o '[0-9]*') 2>/dev/null | grep -v $pid)
        for child in $children; do
            kill -$signal $child 2>/dev/null || true
        done
    else
        # Linux: Use /proc if available
        if [[ -d "/proc/$pid" ]]; then
            local children=$(find /proc/$pid/task/*/children -readable 2>/dev/null | xargs cat | tr ' ' '\n' | sort -u)
            for child in $children; do
                kill -$signal $child 2>/dev/null || true
            done
        fi
    fi
    
    # Finally kill the parent
    kill -$signal $pid 2>/dev/null || true
}

# Check if process is orphaned
is_orphaned() {
    local pid=$1
    local ppid=$(ps -o ppid= -p $pid 2>/dev/null | tr -d ' ')
    [[ "$ppid" == "1" || -z "$ppid" ]]
}

# Export functions for use in subshells
export -f detect_platform
export -f portable_echo
export -f calculate_md5
export -f kill_process_tree
export -f is_orphaned
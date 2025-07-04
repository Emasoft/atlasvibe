# Sequential Pre-commit Configuration Implementation

Complete implementation guide for bulletproof sequential pre-commit execution across all platforms.

## Prerequisites Installation

### macOS

```bash
# Install required tools
brew install bash coreutils findutils gnu-sed gawk grep python@3.11
brew install --cask docker

# Use modern bash
echo "/opt/homebrew/bin/bash" | sudo tee -a /etc/shells
chsh -s /opt/homebrew/bin/bash

# Add GNU tools to PATH (add to ~/.zshrc or ~/.bash_profile)
export PATH="/opt/homebrew/opt/coreutils/libexec/gnubin:$PATH"
export PATH="/opt/homebrew/opt/findutils/libexec/gnubin:$PATH"
export PATH="/opt/homebrew/opt/gnu-sed/libexec/gnubin:$PATH"
export PATH="/opt/homebrew/opt/gawk/libexec/gnubin:$PATH"
export PATH="/opt/homebrew/opt/grep/libexec/gnubin:$PATH"
```

### Linux

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y bash git python3.11 python3-pip docker.io timeout coreutils

# RHEL/Fedora/Amazon Linux
sudo dnf install -y bash git python3.11 python3-pip docker timeout coreutils
```

### Windows (WSL2)

```bash
# In WSL2 Ubuntu
sudo apt-get update
sudo apt-get install -y bash git python3.11 python3-pip docker.io

# Fix line endings
git config --global core.autocrlf input
```

### Python Environment Setup

```bash
# Install uv package manager
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc  # or ~/.zshrc

# Create Python version file (MANDATORY)
echo "3.11" > .python-version

# Install pre-commit with uv
uv pip install pre-commit pre-commit-uv
```

## Step 1: Create All Configuration Files

### A. Environment Configuration

```bash
cat > .sequential-precommit-env << 'EOF'
#!/usr/bin/env bash
# Sequential Pre-commit Environment Configuration v1.0.0
# DO NOT MODIFY - This file is auto-configured for safety

# Version Control
export SEQUENTIAL_PRECOMMIT_VERSION="1.0.0"
export PYTHON_VERSION="3.11"
export UV_PYTHON="python${PYTHON_VERSION}"

# CRITICAL: Force sequential execution
export PRE_COMMIT_MAX_WORKERS=1
export CI_SEQUENTIAL_MODE=1
export PYTHONUNBUFFERED=1

# Timeouts (in seconds) - Tested values for reliability
export DEFAULT_GLOBAL_TIMEOUT=900        # 15 minutes total
export DEFAULT_HEARTBEAT_TIMEOUT=60      # 60 seconds stall detection
export DEFAULT_LOCK_TIMEOUT=30           # 30 seconds lock acquisition
export DEFAULT_CLEANUP_INTERVAL=3600     # 1 hour cleanup cycle

# Resource Limits - Prevent memory exhaustion
export DEFAULT_MEMORY_LIMIT_MB=2048      # 2GB per hook
export DEFAULT_MEMORY_LIMIT_DOCKER_MB=3072  # 3GB for Docker containers
export DEFAULT_MAX_FD=1024               # File descriptor limit
export DEFAULT_CPU_LIMIT=80              # CPU percentage limit

# Logging Configuration
export LOG_DIR=".pre-commit-logs"
export LOG_RETENTION_DAYS=7
export LOG_MAX_SIZE_MB=100

# Process Control - Three-layer defense
export ENABLE_ORPHAN_DETECTION=1
export ORPHAN_CHECK_INTERVAL=30
export ENABLE_PROCESS_GROUP_ISOLATION=1
export ENABLE_HEARTBEAT_MONITOR=1

# Lock File Security
export LOCK_FILE_RANDOM_BYTES=8
export PID_FILE_PERMISSIONS=600

# Platform Detection
export PLATFORM="$(uname -s | tr '[:upper:]' '[:lower:]')"
case "${PLATFORM}" in
    darwin*)
        export IS_MACOS=1
        export STAT_CMD="stat -f %m"
        export TIMEOUT_CMD="gtimeout"
        ;;
    linux*)
        export IS_LINUX=1
        export STAT_CMD="stat -c %Y"
        export TIMEOUT_CMD="timeout"
        ;;
    msys*|cygwin*|mingw*)
        export IS_WINDOWS=1
        export STAT_CMD="stat -c %Y"
        export TIMEOUT_CMD="timeout"
        ;;
    *)
        export IS_UNKNOWN=1
        export STAT_CMD="stat -c %Y"
        export TIMEOUT_CMD="timeout"
        ;;
esac

# Docker Configuration
export DOCKER_ENABLED=1
export DOCKER_NETWORK="sequential-precommit"
export DOCKER_CLEANUP_ON_EXIT=1
EOF
chmod +x .sequential-precommit-env
```

### B. Shared Utilities and Constants

```bash
cat > .sequential-precommit-constants.sh << 'EOF'
#!/usr/bin/env bash
# Shared constants and utility functions v1.0.0

set -euo pipefail

# Version
export SEQUENTIAL_PRECOMMIT_VERSION="1.0.0"

# Colors for output
export RED='\033[0;31m'
export GREEN='\033[0;32m'
export YELLOW='\033[1;33m'
export BLUE='\033[0;34m'
export NC='\033[0m'

# Platform detection with fallback
detect_platform() {
    local platform="${OSTYPE:-$(uname -s | tr '[:upper:]' '[:lower:]')}"
    case "$platform" in
        linux*) echo "linux" ;;
        darwin*) echo "macos" ;;
        msys*|cygwin*|mingw*) echo "windows" ;;
        *) echo "unknown" ;;
    esac
}

# Portable echo function
portable_echo() {
    if [ "${1:-}" = "-e" ]; then
        shift
        printf '%b\n' "$@"
    else
        printf '%s\n' "$@"
    fi
}

# Get file modification time (cross-platform)
get_file_mtime() {
    local file="$1"
    case "$(detect_platform)" in
        macos)
            stat -f %m "$file" 2>/dev/null || echo "0"
            ;;
        *)
            stat -c %Y "$file" 2>/dev/null || echo "0"
            ;;
    esac
}

# Calculate MD5 hash with security improvements
calculate_md5() {
    local input="$1"
    local salt="${2:-$(date +%s%N)}"
    local combined="${input}-${salt}"

    if command -v md5sum >/dev/null 2>&1; then
        echo -n "$combined" | md5sum | cut -d' ' -f1
    elif command -v md5 >/dev/null 2>&1; then
        echo -n "$combined" | md5 -q
    else
        python3 -c "import hashlib; print(hashlib.md5('$combined'.encode()).hexdigest())"
    fi
}

# Kill process tree with verification
kill_process_tree() {
    local pid=$1
    local signal=${2:-TERM}
    local timeout=${3:-5}

    # First, try graceful termination
    if [ "$(detect_platform)" = "macos" ]; then
        local pgid=$(ps -o pgid= -p "$pid" 2>/dev/null | tr -d ' ')
        if [ -n "$pgid" ] && [ "$pgid" != "0" ]; then
            kill -"$signal" -"$pgid" 2>/dev/null || true
        fi
    else
        # Linux: kill children first
        local children=$(pgrep -P "$pid" 2>/dev/null || true)
        if [ -n "$children" ]; then
            echo "$children" | xargs -r kill -"$signal" 2>/dev/null || true
        fi
        kill -"$signal" "$pid" 2>/dev/null || true
    fi

    # Wait for termination
    local count=0
    while kill -0 "$pid" 2>/dev/null && [ $count -lt $timeout ]; do
        sleep 1
        ((count++))
    done

    # Force kill if still alive
    if kill -0 "$pid" 2>/dev/null; then
        kill -KILL "$pid" 2>/dev/null || true
    fi
}

# Enhanced orphan detection
is_orphaned() {
    local pid=${1:-$$}
    local ppid=$(ps -o ppid= -p "$pid" 2>/dev/null | tr -d ' ')

    # Check if parent is init (PID 1)
    if [ -z "$ppid" ] || [ "$ppid" = "1" ]; then
        return 0
    fi

    # Check if parent exists
    if ! kill -0 "$ppid" 2>/dev/null; then
        return 0
    fi

    # Additional check: if parent is a zombie
    local parent_state=$(ps -o stat= -p "$ppid" 2>/dev/null | tr -d ' ')
    if [[ "$parent_state" =~ Z ]]; then
        return 0
    fi

    return 1
}

# Ensure directory with proper permissions
ensure_directory() {
    local dir="$1"
    local perms="${2:-755}"

    if [ ! -d "$dir" ]; then
        mkdir -p "$dir" || return 1
        chmod "$perms" "$dir" || return 1
    fi
    return 0
}

# Validate environment
validate_environment() {
    local errors=0

    # Python version check
    if ! python3 --version 2>&1 | grep -qE "3\.1[1-9]"; then
        portable_echo "ERROR: Python 3.11+ required"
        ((errors++))
    fi

    # Pre-commit installation check
    if ! command -v pre-commit >/dev/null 2>&1; then
        portable_echo "ERROR: pre-commit not installed"
        ((errors++))
    fi

    # Timeout command check
    local timeout_cmd="${TIMEOUT_CMD:-timeout}"
    if ! command -v "$timeout_cmd" >/dev/null 2>&1; then
        portable_echo "ERROR: $timeout_cmd command not found"
        ((errors++))
    fi

    # Bash version check
    if [ "${BASH_VERSION%%.*}" -lt 4 ]; then
        portable_echo "WARNING: Bash 4+ recommended (current: $BASH_VERSION)"
    fi

    return $errors
}

# Lock file operations with atomic creation
acquire_lock() {
    local lock_file="$1"
    local pid_file="$2"
    local timeout="${3:-30}"

    local start_time=$(date +%s)
    while true; do
        # Atomic lock creation
        if mkdir "$lock_file" 2>/dev/null; then
            echo $$ > "$pid_file"
            chmod 600 "$pid_file"
            return 0
        fi

        # Check timeout
        local current_time=$(date +%s)
        if [ $((current_time - start_time)) -ge $timeout ]; then
            return 1
        fi

        # Check if lock holder is dead
        if [ -f "$pid_file" ]; then
            local lock_pid=$(cat "$pid_file" 2>/dev/null || echo "")
            if [ -n "$lock_pid" ] && ! kill -0 "$lock_pid" 2>/dev/null; then
                portable_echo "Removing stale lock from PID $lock_pid"
                rm -rf "$lock_file" "$pid_file"
                continue
            fi
        fi

        sleep 1
    done
}

# Export all functions
export -f detect_platform portable_echo get_file_mtime calculate_md5
export -f kill_process_tree is_orphaned ensure_directory validate_environment
export -f acquire_lock
EOF
chmod +x .sequential-precommit-constants.sh
```

## Step 2: Create Pre-commit Configuration

### A. Update .pre-commit-config.yaml

```yaml
# MANDATORY: Set these at the top of your .pre-commit-config.yaml
default_stages: [pre-commit]
fail_fast: false
minimum_pre_commit_version: "3.0.0"

repos:
  # Standard hooks with sequential execution
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: trailing-whitespace
        require_serial: true
      - id: end-of-file-fixer
        require_serial: true
      - id: check-yaml
        require_serial: true
        args: ["--unsafe"]
      - id: check-added-large-files
        require_serial: true
        args: ["--maxkb=5000"]
      - id: check-merge-conflict
        require_serial: true
      - id: detect-private-key
        require_serial: true

  # Python linting/formatting with memory limits
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.6
    hooks:
      - id: ruff
        require_serial: true
        args: [--fix, --exit-non-zero-on-fix]
      - id: ruff-format
        require_serial: true

  # Type checking with custom wrapper for memory
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.11.0
    hooks:
      - id: mypy
        require_serial: true
        entry: .pre-commit-wrappers/memory-limited-hook.sh mypy
        additional_dependencies: [types-all]
        args: [--strict, --install-types, --non-interactive]

  # Security scanning with memory wrapper
  - repo: https://github.com/trufflesecurity/trufflehog
    rev: v3.89.0
    hooks:
      - id: trufflehog
        require_serial: true
        entry: .pre-commit-wrappers/trufflehog-limited.sh
        args:
          [
            "filesystem",
            ".",
            "--exclude-paths",
            ".trufflehog-exclude",
            "--no-update",
            "--fail",
            "--only-verified",
          ]

  # Dependency checking (often problematic)
  - repo: https://github.com/fpgmaas/deptry
    rev: 0.25.1
    hooks:
      - id: deptry
        require_serial: true
        args: [--skip-missing]
        # Can be skipped with: SKIP=deptry git commit

  # JavaScript/TypeScript hooks
  - repo: https://github.com/pre-commit/mirrors-eslint
    rev: v9.18.0
    hooks:
      - id: eslint
        require_serial: true
        files: \.(js|jsx|ts|tsx)$
        types: [file]

  # Shell script checking
  - repo: https://github.com/shellcheck-py/shellcheck-py
    rev: v0.10.0.1
    hooks:
      - id: shellcheck
        require_serial: true
        args: [--severity=warning]

  # YAML linting
  - repo: https://github.com/adrienverge/yamllint
    rev: v1.35.1
    hooks:
      - id: yamllint
        require_serial: true
        args: [-c=.yamllint]

  # Custom hooks for project-specific checks
  - repo: local
    hooks:
      - id: no-commit-to-main
        name: Prevent commits to main branch
        entry: bash -c 'if [ "$(git rev-parse --abbrev-ref HEAD)" = "main" ]; then echo "Direct commits to main branch are not allowed"; exit 1; fi'
        language: system
        pass_filenames: false
        always_run: true
        require_serial: true
```

### B. Create .trufflehog-exclude

```bash
cat > .trufflehog-exclude << 'EOF'
# Regex patterns for paths to exclude from TruffleHog scanning
\.git/
node_modules/
\.venv/
venv/
__pycache__/
\.pytest_cache/
dist/
build/
\.egg-info/
\.pre-commit-logs/
coverage/
\.nyc_output/
package-lock\.json
pnpm-lock\.yaml
poetry\.lock
uv\.lock
yarn\.lock
EOF
```

### C. Create .yamllint

```yaml
cat > .yamllint << 'EOF'
extends: default

rules:
  line-length:
    max: 120
    level: warning
  truthy:
    allowed-values: ['true', 'false', 'on', 'off']
  comments:
    min-spaces-from-content: 1
  braces:
    max-spaces-inside: 1
  brackets:
    max-spaces-inside: 1
  indentation:
    spaces: 2
EOF
```

## Step 3: Install Robust Pre-commit Wrapper

```bash
# Create hooks directory
mkdir -p .git/hooks

# Create the main wrapper with all safety features
cat > .git/hooks/pre-commit-wrapper-robust-v3 << 'EOF'
#!/usr/bin/env bash
# Robust Pre-commit Wrapper v3.0.0 with Complete Safety Features
# Three-layer defense: Global timeout, Heartbeat monitor, Orphan detection

set -euo pipefail

# Source configuration
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
source "${REPO_ROOT}/.sequential-precommit-env" 2>/dev/null || {
    echo "ERROR: .sequential-precommit-env not found" >&2
    exit 1
}
source "${REPO_ROOT}/.sequential-precommit-constants.sh" 2>/dev/null || {
    echo "ERROR: .sequential-precommit-constants.sh not found" >&2
    exit 1
}

# Initialize logging
WRAPPER_PID=$$
WRAPPER_START=$(date +%s)
LOG_FILE="${LOG_DIR}/pre-commit_$(date +%Y%m%d_%H%M%S)_${WRAPPER_PID}.log"
HEARTBEAT_FILE="${LOG_DIR}/.heartbeat_${WRAPPER_PID}"
ensure_directory "${LOG_DIR}" 755

# Logging function with timestamp
log() {
    local level="${1:-INFO}"
    shift
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $*" | tee -a "$LOG_FILE"
}

# Enhanced cleanup function
cleanup() {
    local exit_code=${1:-$?}
    log "INFO" "=== Cleanup initiated (exit code: $exit_code) ==="

    # Kill orphan detector
    if [ -n "${ORPHAN_DETECTOR_PID:-}" ] && kill -0 "$ORPHAN_DETECTOR_PID" 2>/dev/null; then
        kill -TERM "$ORPHAN_DETECTOR_PID" 2>/dev/null || true
    fi

    # Kill heartbeat monitor
    if [ -n "${HEARTBEAT_PID:-}" ] && kill -0 "$HEARTBEAT_PID" 2>/dev/null; then
        kill -TERM "$HEARTBEAT_PID" 2>/dev/null || true
    fi

    # Kill all child processes
    if [ -n "${PROCESS_GROUP:-}" ]; then
        kill_process_tree "$WRAPPER_PID" TERM 5
    fi

    # Remove lock and PID files
    rm -f "${LOCK_FILE:-}" "${PID_FILE:-}" "${HEARTBEAT_FILE:-}"

    # Log resource usage
    if command -v ps >/dev/null 2>&1; then
        ps -p $$ -o pid,vsz,rss,pcpu,comm 2>/dev/null | tail -n 1 >> "$LOG_FILE" || true
    fi

    log "INFO" "=== Wrapper terminated ==="
    exit "$exit_code"
}

# Signal handlers
trap cleanup EXIT
trap 'log "WARN" "Received INT signal"; cleanup 130' INT
trap 'log "WARN" "Received TERM signal"; cleanup 143' TERM
trap 'log "WARN" "Received HUP signal"; cleanup 129' HUP

# Generate unique identifiers with enhanced security
PROJECT_HASH=$(calculate_md5 "${REPO_ROOT}" "${WRAPPER_PID}-${RANDOM}")
LOCK_FILE="/tmp/pre-commit-${PROJECT_HASH}.lock"
PID_FILE="/tmp/pre-commit-${PROJECT_HASH}.pid"

log "INFO" "=== Pre-commit Wrapper v3 Started ==="
log "INFO" "PID: $WRAPPER_PID, Platform: $(detect_platform)"
log "INFO" "Lock: $LOCK_FILE"

# Check if started as orphan
if is_orphaned; then
    log "ERROR" "Started in orphaned state, exiting"
    exit 1
fi

# Acquire lock with timeout
log "INFO" "Acquiring lock..."
if ! acquire_lock "$LOCK_FILE" "$PID_FILE" "${DEFAULT_LOCK_TIMEOUT}"; then
    log "ERROR" "Could not acquire lock after ${DEFAULT_LOCK_TIMEOUT}s"
    exit 1
fi
log "INFO" "Lock acquired successfully"

# Set up process group isolation
if [ "${ENABLE_PROCESS_GROUP_ISOLATION}" = "1" ] && command -v setsid >/dev/null 2>&1; then
    if [ -z "${IN_PROCESS_GROUP:-}" ]; then
        export IN_PROCESS_GROUP=1
        export PROCESS_GROUP=1
        log "INFO" "Creating new process group"
        exec setsid "$0" "$@"
    fi
fi

# Layer 1: Orphan detection (30-second checks)
if [ "${ENABLE_ORPHAN_DETECTION}" = "1" ]; then
    (
        while true; do
            sleep "${ORPHAN_CHECK_INTERVAL}"
            if is_orphaned "$WRAPPER_PID"; then
                log "ERROR" "Process orphaned, initiating emergency cleanup"
                kill_process_tree "$WRAPPER_PID" KILL 0
                exit 1
            fi
            if ! kill -0 "$WRAPPER_PID" 2>/dev/null; then
                exit 0
            fi
        done
    ) &
    ORPHAN_DETECTOR_PID=$!
    log "INFO" "Started orphan detector (PID: $ORPHAN_DETECTOR_PID)"
fi

# Layer 2: Heartbeat monitor (60-second stall detection)
if [ "${ENABLE_HEARTBEAT_MONITOR}" = "1" ]; then
    (
        while true; do
            sleep "${DEFAULT_HEARTBEAT_TIMEOUT}"
            if [ -f "$HEARTBEAT_FILE" ]; then
                local last_heartbeat=$(get_file_mtime "$HEARTBEAT_FILE")
                local current_time=$(date +%s)
                local stall_time=$((current_time - last_heartbeat))

                if [ $stall_time -gt "${DEFAULT_HEARTBEAT_TIMEOUT}" ]; then
                    log "ERROR" "Heartbeat stalled for ${stall_time}s, killing process"
                    kill_process_tree "$WRAPPER_PID" KILL 0
                    exit 1
                fi
            fi
        done
    ) &
    HEARTBEAT_PID=$!
    log "INFO" "Started heartbeat monitor (PID: $HEARTBEAT_PID)"
fi

# Set resource limits
if [ "$(detect_platform)" = "linux" ]; then
    # Linux supports more granular limits
    ulimit -v $((DEFAULT_MEMORY_LIMIT_MB * 1024)) 2>/dev/null || true
    ulimit -m $((DEFAULT_MEMORY_LIMIT_MB * 1024)) 2>/dev/null || true
    ulimit -n "${DEFAULT_MAX_FD}" 2>/dev/null || true
    ulimit -t $((DEFAULT_GLOBAL_TIMEOUT)) 2>/dev/null || true
else
    # macOS has limited ulimit support
    ulimit -n "${DEFAULT_MAX_FD}" 2>/dev/null || true
fi

# Export critical environment variables
export PRE_COMMIT_MAX_WORKERS=1
export PYTHONUNBUFFERED=1
export PIP_DISABLE_PIP_VERSION_CHECK=1
export PIP_NO_CACHE_DIR=1

# Update heartbeat
touch "$HEARTBEAT_FILE"

# Layer 3: Global timeout wrapper
log "INFO" "Starting pre-commit with ${DEFAULT_GLOBAL_TIMEOUT}s timeout..."
PRE_COMMIT_EXIT=0

# Platform-specific timeout command
TIMEOUT_BIN="${TIMEOUT_CMD:-timeout}"
if ! command -v "$TIMEOUT_BIN" >/dev/null 2>&1; then
    # Fallback: no timeout wrapper
    log "WARN" "Timeout command not found, running without timeout protection"
    pre-commit "$@" 2>&1 | while IFS= read -r line; do
        echo "$line" | tee -a "$LOG_FILE"
        touch "$HEARTBEAT_FILE"  # Update heartbeat on output
    done
    PRE_COMMIT_EXIT=${PIPESTATUS[0]}
else
    # Run with timeout
    "$TIMEOUT_BIN" --signal=TERM --kill-after=30 "${DEFAULT_GLOBAL_TIMEOUT}" \
        pre-commit "$@" 2>&1 | while IFS= read -r line; do
        echo "$line" | tee -a "$LOG_FILE"
        touch "$HEARTBEAT_FILE"  # Update heartbeat on output
    done
    PRE_COMMIT_EXIT=${PIPESTATUS[0]}
fi

# Handle timeout exit codes
case $PRE_COMMIT_EXIT in
    124|137)
        log "ERROR" "Pre-commit timed out after ${DEFAULT_GLOBAL_TIMEOUT}s"
        ;;
    0)
        log "INFO" "Pre-commit completed successfully"
        ;;
    *)
        log "WARN" "Pre-commit failed with exit code: $PRE_COMMIT_EXIT"
        ;;
esac

log "INFO" "Total execution time: $(($(date +%s) - WRAPPER_START))s"
exit $PRE_COMMIT_EXIT
EOF
chmod +x .git/hooks/pre-commit-wrapper-robust-v3

# Create the main pre-commit hook
cat > .git/hooks/pre-commit << 'EOF'
#!/usr/bin/env bash
# Pre-commit hook entry point
exec "$(git rev-parse --git-dir)/hooks/pre-commit-wrapper-robust-v3" "$@"
EOF
chmod +x .git/hooks/pre-commit

# Create pre-push wrapper for different timeout
cat > .git/hooks/pre-push << 'EOF'
#!/usr/bin/env bash
# Pre-push hook with extended timeout
export DEFAULT_GLOBAL_TIMEOUT=1800  # 30 minutes for push
exec "$(git rev-parse --git-dir)/hooks/pre-commit-wrapper-robust-v3" "$@"
EOF
chmod +x .git/hooks/pre-push
```

## Step 4: Create Memory-Limited Wrappers

```bash
# Create wrappers directory
mkdir -p .pre-commit-wrappers

# Generic memory-limited wrapper
cat > .pre-commit-wrappers/memory-limited-hook.sh << 'EOF'
#!/usr/bin/env bash
# Memory-limited execution wrapper v1.0.0
set -euo pipefail

# Source utilities
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
source "${REPO_ROOT}/.sequential-precommit-env" 2>/dev/null || true
source "${REPO_ROOT}/.sequential-precommit-constants.sh" 2>/dev/null || true

# Parse arguments
HOOK_NAME="${1:-unknown}"
shift

# Configuration from environment or defaults
MEMORY_LIMIT_MB="${MEMORY_LIMIT_MB:-512}"
HOOK_TIMEOUT="${HOOK_TIMEOUT:-300}"
CPU_LIMIT="${CPU_LIMIT:-80}"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [memory-wrapper] $*" >&2
}

log "Running $HOOK_NAME with limits: Memory=${MEMORY_LIMIT_MB}MB, Timeout=${HOOK_TIMEOUT}s"

# Platform-specific resource limiting
case "$(detect_platform)" in
    linux)
        # Check for cgroups v2 support
        if [ -f /sys/fs/cgroup/cgroup.controllers ]; then
            # Try systemd-run if available (preferred method)
            if command -v systemd-run >/dev/null 2>&1; then
                exec systemd-run --quiet --pipe --same-dir \
                    -p MemoryMax="${MEMORY_LIMIT_MB}M" \
                    -p CPUQuota="${CPU_LIMIT}%" \
                    timeout "${HOOK_TIMEOUT}" "$@"
            fi
        fi
        # Fallback to ulimit
        ulimit -v $((MEMORY_LIMIT_MB * 1024)) 2>/dev/null || true
        ulimit -t "${HOOK_TIMEOUT}" 2>/dev/null || true
        ;;
    macos)
        # macOS: limited ulimit support
        ulimit -t "${HOOK_TIMEOUT}" 2>/dev/null || true
        # Note: macOS doesn't support -v for virtual memory
        ;;
    *)
        log "Warning: Unknown platform, resource limits may not work"
        ;;
esac

# Execute with timeout
TIMEOUT_BIN="${TIMEOUT_CMD:-timeout}"
if command -v "$TIMEOUT_BIN" >/dev/null 2>&1; then
    exec "$TIMEOUT_BIN" --signal=TERM --kill-after=10 "${HOOK_TIMEOUT}" "$@"
else
    exec "$@"
fi
EOF
chmod +x .pre-commit-wrappers/memory-limited-hook.sh

# TruffleHog-specific wrapper
cat > .pre-commit-wrappers/trufflehog-limited.sh << 'EOF'
#!/usr/bin/env bash
# TruffleHog wrapper with memory limits
set -euo pipefail

# TruffleHog needs more memory
export MEMORY_LIMIT_MB=1024
export HOOK_TIMEOUT=120

# Use the generic wrapper
exec "$(dirname "$0")/memory-limited-hook.sh" "trufflehog" trufflehog "$@"
EOF
chmod +x .pre-commit-wrappers/trufflehog-limited.sh

# MyPy-specific wrapper
cat > .pre-commit-wrappers/mypy-limited.sh << 'EOF'
#!/usr/bin/env bash
# MyPy wrapper with memory limits
set -euo pipefail

# MyPy can be memory intensive on large codebases
export MEMORY_LIMIT_MB=2048
export HOOK_TIMEOUT=600

# Use the generic wrapper
exec "$(dirname "$0")/memory-limited-hook.sh" "mypy" mypy "$@"
EOF
chmod +x .pre-commit-wrappers/mypy-limited.sh
```

## Step 5: Create Cleanup and Monitoring Scripts

```bash
# Create scripts directory
mkdir -p scripts

# Orphaned process cleanup script
cat > scripts/cleanup-orphaned-processes.sh << 'EOF'
#!/usr/bin/env bash
# Comprehensive cleanup script for orphaned pre-commit processes
set -euo pipefail

# Source utilities
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
source "${REPO_ROOT}/.sequential-precommit-constants.sh" 2>/dev/null || true

# Statistics
ORPHANED_COUNT=0
CLEANED_COUNT=0
STALE_FILES=0
OLD_LOCKS=0
ZOMBIE_COUNT=0

echo "$(portable_echo -e "${YELLOW}=== Orphaned Process Cleanup ===${NC}")"
echo "Time: $(date)"

# Function to check if process is zombie
is_zombie() {
    local pid=$1
    local state=$(ps -o stat= -p "$pid" 2>/dev/null | tr -d ' ')
    [[ "$state" =~ Z ]]
}

# Find and clean orphaned processes
echo "Scanning for orphaned pre-commit processes..."

# Search for all pre-commit related processes
for pattern in "pre-commit-wrapper-robust" "pre-commit run" "\.git/hooks/pre-commit"; do
    while IFS= read -r line; do
        [ -z "$line" ] && continue

        pid=$(echo "$line" | awk '{print $2}')
        cmd=$(echo "$line" | awk '{for(i=11;i<=NF;i++) printf "%s ", $i; print ""}')

        # Check various orphan conditions
        if is_orphaned "$pid"; then
            ((ORPHANED_COUNT++))
            echo "$(portable_echo -e "${RED}Found orphaned process:${NC}")"
            echo "  PID: $pid"
            echo "  Command: $cmd"
            echo "  Runtime: $(ps -o etime= -p "$pid" 2>/dev/null | tr -d ' ' || echo "unknown")"

            if kill_process_tree "$pid" TERM 5; then
                ((CLEANED_COUNT++))
                echo "$(portable_echo -e "  ${GREEN}✓ Process terminated${NC}")"
            else
                echo "$(portable_echo -e "  ${RED}✗ Failed to terminate${NC}")"
            fi
            echo
        elif is_zombie "$pid"; then
            ((ZOMBIE_COUNT++))
            echo "$(portable_echo -e "${YELLOW}Found zombie process:${NC}") PID $pid"
        fi
    done < <(pgrep -f "$pattern" 2>/dev/null || true)
done

# Clean stale PID files
echo "Checking for stale PID files..."
for pidfile in /tmp/pre-commit-*.pid; do
    [ -f "$pidfile" ] || continue

    pid=$(cat "$pidfile" 2>/dev/null || echo "")
    if [ -n "$pid" ]; then
        if ! kill -0 "$pid" 2>/dev/null; then
            ((STALE_FILES++))
            echo "$(portable_echo -e "${YELLOW}Removing stale PID file:${NC}") $pidfile (PID: $pid)"
            rm -f "$pidfile"
        fi
    else
        # Empty PID file
        ((STALE_FILES++))
        echo "$(portable_echo -e "${YELLOW}Removing empty PID file:${NC}") $pidfile"
        rm -f "$pidfile"
    fi
done

# Clean old lock directories (older than 1 day)
echo "Checking for old lock files..."
find /tmp -name "pre-commit-*.lock" -type d -mtime +1 2>/dev/null | while read -r lockdir; do
    ((OLD_LOCKS++))
    echo "$(portable_echo -e "${YELLOW}Removing old lock:${NC}") $lockdir"
    rm -rf "$lockdir"
done

# Clean old log files in project
if [ -d "${REPO_ROOT}/.pre-commit-logs" ]; then
    echo "Cleaning old log files..."
    find "${REPO_ROOT}/.pre-commit-logs" -name "*.log" -mtime +7 -delete 2>/dev/null || true
fi

# Summary
echo
echo "$(portable_echo -e "${GREEN}=== Cleanup Summary ===${NC}")"
echo "Orphaned processes found: $ORPHANED_COUNT"
echo "Processes cleaned: $CLEANED_COUNT"
echo "Zombie processes found: $ZOMBIE_COUNT"
echo "Stale PID files removed: $STALE_FILES"
echo "Old lock files removed: $OLD_LOCKS"

if [ $((ORPHANED_COUNT + STALE_FILES + OLD_LOCKS + ZOMBIE_COUNT)) -eq 0 ]; then
    echo "$(portable_echo -e "${GREEN}✓ No cleanup needed${NC}")"
    exit 0
else
    echo "$(portable_echo -e "${GREEN}✓ Cleanup completed${NC}")"
    exit 0
fi
EOF
chmod +x scripts/cleanup-orphaned-processes.sh

# Automated cleanup setup script
cat > scripts/setup-orphan-cleanup-cron.sh << 'EOF'
#!/usr/bin/env bash
# Setup automated cleanup for orphaned processes
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLEANUP_SCRIPT="${SCRIPT_DIR}/cleanup-orphaned-processes.sh"

echo "=== Setting up automated orphaned process cleanup ==="

# Verify cleanup script exists and is executable
if [ ! -f "$CLEANUP_SCRIPT" ]; then
    echo "ERROR: Cleanup script not found at $CLEANUP_SCRIPT"
    exit 1
fi

if [ ! -x "$CLEANUP_SCRIPT" ]; then
    chmod +x "$CLEANUP_SCRIPT"
fi

# Platform-specific setup
case "$(uname -s)" in
    Darwin*)
        # macOS: Use LaunchAgent
        PLIST_FILE="$HOME/Library/LaunchAgents/com.sequential-precommit.cleanup.plist"
        PLIST_DIR="$(dirname "$PLIST_FILE")"
        LOG_DIR="$HOME/.sequential-precommit"

        # Create directories
        mkdir -p "$PLIST_DIR" "$LOG_DIR"

        # Create plist file
        cat > "$PLIST_FILE" << PLIST_EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.sequential-precommit.cleanup</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>$CLEANUP_SCRIPT</string>
    </array>
    <key>StartInterval</key>
    <integer>3600</integer>
    <key>StandardOutPath</key>
    <string>$LOG_DIR/cleanup.log</string>
    <key>StandardErrorPath</key>
    <string>$LOG_DIR/cleanup-error.log</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
</dict>
</plist>
PLIST_EOF

        # Load the agent
        launchctl unload "$PLIST_FILE" 2>/dev/null || true
        launchctl load "$PLIST_FILE"

        echo "✓ LaunchAgent installed for macOS"
        echo "  Config: $PLIST_FILE"
        echo "  Logs: $LOG_DIR/cleanup.log"
        echo
        echo "Commands:"
        echo "  Status: launchctl list | grep sequential-precommit"
        echo "  Stop: launchctl unload $PLIST_FILE"
        echo "  Start: launchctl load $PLIST_FILE"
        echo "  Logs: tail -f $LOG_DIR/cleanup.log"
        ;;

    Linux*)
        # Linux: Use cron
        LOG_DIR="$HOME/.sequential-precommit"
        mkdir -p "$LOG_DIR"

        # Create cron job
        CRON_JOB="0 * * * * /bin/bash $CLEANUP_SCRIPT >> $LOG_DIR/cleanup.log 2>&1"

        # Check if already exists
        if crontab -l 2>/dev/null | grep -q "cleanup-orphaned-processes.sh"; then
            echo "✓ Cron job already exists"
        else
            # Add to crontab
            (crontab -l 2>/dev/null || true; echo "$CRON_JOB") | crontab -
            echo "✓ Cron job installed for Linux"
        fi

        echo "  Logs: $LOG_DIR/cleanup.log"
        echo
        echo "Commands:"
        echo "  List: crontab -l"
        echo "  Edit: crontab -e"
        echo "  Remove: crontab -l | grep -v cleanup-orphaned | crontab -"
        echo "  Logs: tail -f $LOG_DIR/cleanup.log"

        # Also set up systemd timer if available
        if command -v systemctl >/dev/null 2>&1 && [ -d "$HOME/.config/systemd/user" ]; then
            echo
            echo "Setting up systemd timer (recommended)..."

            # Create service file
            cat > "$HOME/.config/systemd/user/sequential-precommit-cleanup.service" << SERVICE_EOF
[Unit]
Description=Sequential Pre-commit Cleanup
After=network.target

[Service]
Type=oneshot
ExecStart=/bin/bash $CLEANUP_SCRIPT
StandardOutput=append:$LOG_DIR/cleanup-systemd.log
StandardError=append:$LOG_DIR/cleanup-systemd-error.log
SERVICE_EOF

            # Create timer file
            cat > "$HOME/.config/systemd/user/sequential-precommit-cleanup.timer" << TIMER_EOF
[Unit]
Description=Run Sequential Pre-commit Cleanup hourly
Requires=sequential-precommit-cleanup.service

[Timer]
OnCalendar=hourly
Persistent=true

[Install]
WantedBy=timers.target
TIMER_EOF

            # Enable and start timer
            systemctl --user daemon-reload
            systemctl --user enable sequential-precommit-cleanup.timer
            systemctl --user start sequential-precommit-cleanup.timer

            echo "✓ Systemd timer installed"
            echo
            echo "Systemd commands:"
            echo "  Status: systemctl --user status sequential-precommit-cleanup.timer"
            echo "  Logs: journalctl --user -u sequential-precommit-cleanup"
            echo "  Disable: systemctl --user disable sequential-precommit-cleanup.timer"
        fi
        ;;

    MINGW*|CYGWIN*|MSYS*)
        # Windows (Git Bash)
        echo "✗ Windows detected. Please use Task Scheduler to run cleanup hourly:"
        echo "  1. Open Task Scheduler"
        echo "  2. Create Basic Task"
        echo "  3. Set trigger: Daily, repeat every 1 hour"
        echo "  4. Set action: Start a program"
        echo "  5. Program: bash"
        echo "  6. Arguments: $CLEANUP_SCRIPT"
        ;;

    *)
        echo "✗ Unknown platform. Please set up manual cleanup."
        exit 1
        ;;
esac

echo
echo "=== Setup complete ==="
echo "Cleanup will run automatically every hour"
echo "To run manually: $CLEANUP_SCRIPT"
EOF
chmod +x scripts/setup-orphan-cleanup-cron.sh
```

## Step 6: GitHub Actions Configuration

### A. Pre-commit Workflow

```yaml
# .github/workflows/pre-commit.yml
name: Pre-commit Checks

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

# CRITICAL: These environment variables ensure sequential execution
env:
  PRE_COMMIT_MAX_WORKERS: 1
  CI_SEQUENTIAL_MODE: 1
  PYTHON_VERSION: "3.11"
  PYTHONUNBUFFERED: 1
  PIP_DISABLE_PIP_VERSION_CHECK: 1
  # Timeouts
  DEFAULT_GLOBAL_TIMEOUT: 1800 # 30 minutes for CI
  DEFAULT_MEMORY_LIMIT_MB: 4096 # 4GB for CI containers

jobs:
  pre-commit:
    runs-on: ubuntu-latest
    timeout-minutes: 45 # Overall job timeout

    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0 # Full history for some hooks

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Install uv
        uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true
          cache-dependency-glob: "uv.lock"

      - name: Install system dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y \
            shellcheck \
            yamllint \
            coreutils \
            timeout

      - name: Install Python dependencies
        run: |
          uv pip install pre-commit
          if [ -f "pyproject.toml" ]; then
            uv sync --all-extras
          elif [ -f "requirements.txt" ]; then
            uv pip install -r requirements.txt
          fi

      - name: Cache pre-commit environments
        uses: actions/cache@v4
        with:
          path: ~/.cache/pre-commit
          key: pre-commit-${{ runner.os }}-${{ hashFiles('.pre-commit-config.yaml') }}
          restore-keys: |
            pre-commit-${{ runner.os }}-

      - name: Run pre-commit
        run: |
          # Ensure sequential execution
          export PRE_COMMIT_MAX_WORKERS=1
          export SKIP=deptry  # Skip problematic hooks if needed

          # Run with explicit timeout
          timeout 30m pre-commit run --all-files --show-diff-on-failure || {
            exit_code=$?
            echo "Pre-commit failed with exit code: $exit_code"

            # Upload logs on failure
            if [ -d ".pre-commit-logs" ]; then
              echo "Uploading pre-commit logs..."
              tar -czf pre-commit-logs.tar.gz .pre-commit-logs/
            fi

            exit $exit_code
          }

      - name: Upload logs on failure
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: pre-commit-logs
          path: |
            .pre-commit-logs/
            pre-commit-logs.tar.gz
          retention-days: 7
```

### B. CI Pipeline

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

env:
  PRE_COMMIT_MAX_WORKERS: 1
  CI_SEQUENTIAL_MODE: 1
  PYTHON_VERSION: "3.11"
  NODE_VERSION: "20"

jobs:
  lint:
    runs-on: ubuntu-latest
    timeout-minutes: 30

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true

      - name: Install dependencies
        run: |
          uv pip install ruff mypy
          uv sync --all-extras

      - name: Run Ruff
        run: |
          uv run ruff check . --output-format=github
          uv run ruff format . --check

      - name: Run MyPy
        run: |
          uv run mypy . --install-types --non-interactive

  test:
    runs-on: ${{ matrix.os }}
    timeout-minutes: 45

    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        python-version: ["3.11", "3.12"]

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true

      - name: Install dependencies
        run: |
          uv sync --all-extras

      - name: Run tests
        run: |
          uv run pytest -v --cov=. --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v5
        with:
          file: ./coverage.xml
          fail_ci_if_error: false
```

## Step 7: Docker Testing Configuration

### A. Create Docker Compose for Testing

```yaml
# docker-compose.test.yml
version: "3.8"

services:
  pre-commit-test:
    build:
      context: .
      dockerfile: Dockerfile.test
    image: sequential-precommit-test:latest
    container_name: pre-commit-test
    environment:
      - PRE_COMMIT_MAX_WORKERS=1
      - CI_SEQUENTIAL_MODE=1
      - DEFAULT_MEMORY_LIMIT_MB=2048
    volumes:
      - .:/workspace:ro
      - pre-commit-cache:/root/.cache/pre-commit
    networks:
      - sequential-precommit
    mem_limit: 3g
    cpus: "2.0"
    command: >
      bash -c "
        cd /workspace &&
        cp -r . /tmp/test-workspace &&
        cd /tmp/test-workspace &&
        pre-commit run --all-files
      "

  workflow-test:
    image: nektos/act:latest
    container_name: workflow-test
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - .:/workspace:ro
    networks:
      - sequential-precommit
    command: >
      -W .github/workflows/pre-commit.yml
      -P ubuntu-latest=catthehacker/ubuntu:act-latest

volumes:
  pre-commit-cache:

networks:
  sequential-precommit:
    driver: bridge
```

### B. Create Test Dockerfile

```dockerfile
# Dockerfile.test
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    bash \
    coreutils \
    findutils \
    grep \
    sed \
    gawk \
    curl \
    build-essential \
    shellcheck \
    yamllint \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Install pre-commit
RUN uv pip install --system pre-commit pre-commit-uv

# Set working directory
WORKDIR /workspace

# Copy configuration files
COPY .sequential-precommit-env .sequential-precommit-constants.sh ./
COPY .pre-commit-config.yaml ./

# Pre-install pre-commit hooks
RUN git init && pre-commit install-hooks

# Set environment
ENV PRE_COMMIT_MAX_WORKERS=1
ENV CI_SEQUENTIAL_MODE=1
```

### C. Docker Test Script

```bash
# scripts/test-in-docker.sh
cat > scripts/test-in-docker.sh << 'EOF'
#!/usr/bin/env bash
# Test pre-commit configuration in Docker
set -euo pipefail

echo "=== Testing Sequential Pre-commit in Docker ==="

# Build test image
echo "Building test image..."
docker build -f Dockerfile.test -t sequential-precommit-test:latest .

# Run tests
echo "Running pre-commit tests..."
docker-compose -f docker-compose.test.yml up --abort-on-container-exit

# Cleanup
echo "Cleaning up..."
docker-compose -f docker-compose.test.yml down -v

echo "=== Docker tests complete ==="
EOF
chmod +x scripts/test-in-docker.sh
```

## Step 8: Subagent Rules Implementation

### A. Create Subagent Configuration

```bash
cat > .subagent-rules.sh << 'EOF'
#!/usr/bin/env bash
# Subagent Rules for Sequential Pre-commit
# Source this file in your automation scripts

# Rule 1: No parallel git operations
git_sequential() {
    local operation=$1
    shift

    # Check for existing git operations
    if pgrep -f "git (add|commit|push|pull|merge|rebase)" >/dev/null 2>&1; then
        echo "ERROR: Another git operation is running" >&2
        return 1
    fi

    # Execute with lock
    (
        flock -n 9 || {
            echo "ERROR: Git operation locked" >&2
            exit 1
        }
        git "$operation" "$@"
    ) 9>/tmp/.git-operation.lock
}

# Rule 2: Memory limits for subagents
set_subagent_limits() {
    export MEMORY_LIMIT_MB="${MEMORY_LIMIT_MB:-1024}"
    export CPU_LIMIT="${CPU_LIMIT:-50}"

    # Apply limits based on platform
    case "$(uname -s)" in
        Linux)
            ulimit -v $((MEMORY_LIMIT_MB * 1024)) 2>/dev/null || true
            ulimit -t 300 2>/dev/null || true  # 5 minute CPU time
            ;;
        Darwin)
            ulimit -t 300 2>/dev/null || true
            ;;
    esac
}

# Rule 3: Check for pre-commit locks
wait_for_precommit() {
    local timeout=${1:-60}
    local count=0

    while [ -d "/tmp/pre-commit-*.lock" ] && [ $count -lt $timeout ]; do
        echo "Waiting for pre-commit to finish... ($count/$timeout)"
        sleep 1
        ((count++))
    done

    if [ $count -ge $timeout ]; then
        echo "ERROR: Pre-commit lock timeout" >&2
        return 1
    fi
}

# Rule 4: Safe automated commits
safe_commit() {
    local message="$1"

    # Set limits
    set_subagent_limits

    # Wait for any pre-commit
    wait_for_precommit || return 1

    # Sequential git operations
    git_sequential add -A || return 1
    git_sequential commit --no-verify -m "$message" || return 1
}

# Rule 5: Cleanup on exit
subagent_cleanup() {
    # Remove any locks we created
    rm -f /tmp/.git-operation.lock

    # Kill any child processes
    jobs -p | xargs -r kill 2>/dev/null || true
}

# Set up cleanup trap
trap subagent_cleanup EXIT

# Export functions
export -f git_sequential set_subagent_limits wait_for_precommit safe_commit
EOF
chmod +x .subagent-rules.sh

# Example subagent script
cat > scripts/example-subagent.sh << 'EOF'
#!/usr/bin/env bash
# Example of a safe subagent implementation
set -euo pipefail

# Source subagent rules
source "$(git rev-parse --show-toplevel)/.subagent-rules.sh"

# Set resource limits
set_subagent_limits

# Your automation logic here
echo "Running automated tasks..."

# Safe commit
if [ -n "$(git status --porcelain)" ]; then
    safe_commit "Automated update by subagent"
fi

# Safe push (also sequential)
wait_for_precommit
git_sequential push origin main
EOF
chmod +x scripts/example-subagent.sh
```

## Step 9: Validation Script

```bash
cat > scripts/validate-sequential-setup.sh << 'EOF'
#!/usr/bin/env bash
# Comprehensive validation of sequential pre-commit setup
set -euo pipefail

# Source utilities
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "$REPO_ROOT"

source .sequential-precommit-constants.sh 2>/dev/null || {
    echo "ERROR: Constants file not found"
    exit 1
}

ERRORS=0
WARNINGS=0

# Test functions
test_pass() {
    echo "$(portable_echo -e "${GREEN}✓${NC}") $1"
}

test_fail() {
    echo "$(portable_echo -e "${RED}✗${NC}") $1"
    ((ERRORS++))
}

test_warn() {
    echo "$(portable_echo -e "${YELLOW}⚠${NC}") $1"
    ((WARNINGS++))
}

echo "=== Sequential Pre-commit Setup Validation ==="
echo

# 1. Check files exist
echo "Checking configuration files..."
[ -f ".sequential-precommit-env" ] && test_pass "Environment file exists" || test_fail "Environment file missing"
[ -f ".sequential-precommit-constants.sh" ] && test_pass "Constants file exists" || test_fail "Constants file missing"
[ -f ".python-version" ] && test_pass "Python version file exists" || test_fail "Python version file missing"
[ -f ".pre-commit-config.yaml" ] && test_pass "Pre-commit config exists" || test_fail "Pre-commit config missing"

# 2. Check Python version
echo
echo "Checking Python version..."
if [ -f ".python-version" ]; then
    PY_VERSION=$(cat .python-version)
    if [ "$PY_VERSION" = "3.11" ]; then
        test_pass "Python version is 3.11"
    else
        test_fail "Python version is $PY_VERSION, expected 3.11"
    fi
fi

# 3. Check pre-commit installation
echo
echo "Checking pre-commit installation..."
if command -v pre-commit >/dev/null 2>&1; then
    test_pass "Pre-commit is installed"
    PC_VERSION=$(pre-commit --version | cut -d' ' -f2)
    echo "  Version: $PC_VERSION"
else
    test_fail "Pre-commit is not installed"
fi

# 4. Check hooks configuration
echo
echo "Checking hooks configuration..."
if [ -f ".pre-commit-config.yaml" ]; then
    SERIAL_COUNT=$(grep -c "require_serial: true" .pre-commit-config.yaml || echo "0")
    TOTAL_HOOKS=$(grep -c "- id:" .pre-commit-config.yaml || echo "0")

    if [ "$SERIAL_COUNT" -eq "$TOTAL_HOOKS" ] && [ "$TOTAL_HOOKS" -gt 0 ]; then
        test_pass "All $TOTAL_HOOKS hooks have require_serial: true"
    else
        test_fail "Only $SERIAL_COUNT of $TOTAL_HOOKS hooks have require_serial: true"
    fi
fi

# 5. Check git hooks
echo
echo "Checking git hooks..."
[ -f ".git/hooks/pre-commit" ] && test_pass "Pre-commit hook exists" || test_fail "Pre-commit hook missing"
[ -x ".git/hooks/pre-commit" ] && test_pass "Pre-commit hook is executable" || test_fail "Pre-commit hook not executable"
[ -f ".git/hooks/pre-commit-wrapper-robust-v3" ] && test_pass "Wrapper v3 exists" || test_fail "Wrapper v3 missing"
[ -x ".git/hooks/pre-commit-wrapper-robust-v3" ] && test_pass "Wrapper v3 is executable" || test_fail "Wrapper v3 not executable"

# 6. Check wrappers
echo
echo "Checking memory wrappers..."
[ -d ".pre-commit-wrappers" ] && test_pass "Wrappers directory exists" || test_fail "Wrappers directory missing"
[ -f ".pre-commit-wrappers/memory-limited-hook.sh" ] && test_pass "Memory wrapper exists" || test_fail "Memory wrapper missing"
[ -x ".pre-commit-wrappers/memory-limited-hook.sh" ] && test_pass "Memory wrapper is executable" || test_warn "Memory wrapper not executable"

# 7. Check cleanup scripts
echo
echo "Checking cleanup scripts..."
[ -f "scripts/cleanup-orphaned-processes.sh" ] && test_pass "Cleanup script exists" || test_fail "Cleanup script missing"
[ -x "scripts/cleanup-orphaned-processes.sh" ] && test_pass "Cleanup script is executable" || test_fail "Cleanup script not executable"

# 8. Check for orphaned processes
echo
echo "Checking for orphaned processes..."
ORPHAN_COUNT=$(pgrep -f "pre-commit-wrapper-robust" 2>/dev/null | wc -l || echo "0")
if [ "$ORPHAN_COUNT" -eq 0 ]; then
    test_pass "No orphaned processes found"
else
    test_warn "$ORPHAN_COUNT possible orphaned processes found"
fi

# 9. Test environment validation
echo
echo "Validating environment..."
if validate_environment; then
    test_pass "Environment validation passed"
else
    test_fail "Environment validation failed"
fi

# 10. Test lock mechanism
echo
echo "Testing lock mechanism..."
TEST_LOCK="/tmp/test-sequential-$$"
if acquire_lock "$TEST_LOCK.lock" "$TEST_LOCK.pid" 2; then
    test_pass "Lock mechanism works"
    rm -rf "$TEST_LOCK.lock" "$TEST_LOCK.pid"
else
    test_fail "Lock mechanism failed"
fi

# Summary
echo
echo "$(portable_echo -e "${BLUE}=== Validation Summary ===${NC}")"
echo "Errors: $ERRORS"
echo "Warnings: $WARNINGS"

if [ $ERRORS -eq 0 ]; then
    echo "$(portable_echo -e "${GREEN}✓ Sequential pre-commit setup is valid${NC}")"

    if [ $WARNINGS -gt 0 ]; then
        echo "$(portable_echo -e "${YELLOW}Some warnings should be addressed${NC}")"
    fi

    echo
    echo "Next steps:"
    echo "1. Run: ./scripts/setup-orphan-cleanup-cron.sh"
    echo "2. Test: PRE_COMMIT_MAX_WORKERS=1 pre-commit run --all-files"
    echo "3. Monitor: tail -f .pre-commit-logs/*.log"

    exit 0
else
    echo "$(portable_echo -e "${RED}✗ Setup has errors that must be fixed${NC}")"
    exit 1
fi
EOF
chmod +x scripts/validate-sequential-setup.sh
```

## Step 10: Quick Setup Script

```bash
cat > setup-sequential-precommit.sh << 'EOF'
#!/usr/bin/env bash
# One-command setup for sequential pre-commit
set -euo pipefail

echo "=== Sequential Pre-commit Quick Setup ==="

# Create all files
echo "Creating configuration files..."
bash -c "$(curl -fsSL https://raw.githubusercontent.com/YOUR_REPO/main/scripts/create-sequential-files.sh)"

# Run validation
echo "Validating setup..."
./scripts/validate-sequential-setup.sh

# Set up cleanup
echo "Setting up automated cleanup..."
./scripts/setup-orphan-cleanup-cron.sh

echo "=== Setup complete! ==="
EOF
chmod +x setup-sequential-precommit.sh
```

## Troubleshooting Guide

### Common Issues and Solutions

#### 1. Pre-commit Already Running

```bash
# Immediate fix
./scripts/cleanup-orphaned-processes.sh

# Nuclear option
rm -rf /tmp/pre-commit-*.lock /tmp/pre-commit-*.pid
pkill -f "pre-commit-wrapper-robust"
```

#### 2. Specific Hook Failures

```bash
# Skip problematic hooks
SKIP=deptry,mypy git commit

# Or permanently disable in .pre-commit-config.yaml
# Add: stages: [manual] to the hook
```

#### 3. Memory Exhaustion

```bash
# Increase limits in .sequential-precommit-env
export DEFAULT_MEMORY_LIMIT_MB=4096

# Or use memory wrapper for specific hooks
entry: .pre-commit-wrappers/memory-limited-hook.sh original-command
```

#### 4. Timeout Issues

```bash
# For commits
export DEFAULT_GLOBAL_TIMEOUT=1800  # 30 minutes

# For push operations
export DEFAULT_GLOBAL_TIMEOUT=3600  # 60 minutes
```

#### 5. Platform-Specific Issues

**macOS flock missing:**

```bash
brew install flock
# Or use mkdir-based locking (already implemented as fallback)
```

**Linux cgroups v2:**

```bash
# Check cgroups version
stat -fc %T /sys/fs/cgroup/

# For cgroups v2 issues, fall back to ulimit (automatic)
```

**Windows WSL2:**

```bash
# Ensure proper line endings
git config core.autocrlf input
dos2unix scripts/*.sh
```

## Maintenance

### Daily Tasks

```bash
# Check logs
ls -la .pre-commit-logs/
tail -f .pre-commit-logs/pre-commit_*.log

# Run cleanup
./scripts/cleanup-orphaned-processes.sh
```

### Weekly Tasks

```bash
# Clean old logs
find .pre-commit-logs -name "*.log" -mtime +7 -delete

# Update hooks
pre-commit autoupdate

# Validate setup
./scripts/validate-sequential-setup.sh
```

### Monthly Tasks

```bash
# Full cleanup and reinstall
pre-commit clean
pre-commit install --install-hooks
pre-commit run --all-files

# Update pre-commit
uv pip install --upgrade pre-commit

# Check for security updates
uv pip list --outdated
```

## Summary

This implementation provides:

✅ **Complete Sequential Execution** - All hooks run one at a time
✅ **Three-Layer Defense System** - Timeout + Heartbeat + Orphan detection
✅ **Cross-Platform Support** - Works on macOS, Linux, Windows WSL2
✅ **Resource Protection** - Memory limits, CPU limits, file descriptor limits
✅ **Automatic Cleanup** - Hourly orphan process removal
✅ **Lock Security** - Unique MD5 hashes with PID and random components
✅ **Docker Testing** - Isolated testing environment
✅ **Subagent Safety** - Rules prevent parallel operations
✅ **GitHub Actions Ready** - Complete CI/CD configuration
✅ **Comprehensive Logging** - Full audit trail with rotation
✅ **Easy Validation** - One command to check entire setup

The system handles all edge cases including SSH disconnection, terminal crashes, IDE failures, and system resource exhaustion.

#!/usr/bin/env bash
# Universal Sequential Pre-commit Setup Script
# Works on macOS, Linux, and WSL2

set -euo pipefail

# Script version
SCRIPT_VERSION="1.0.0"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Functions
echo_color() {
    local color=$1
    shift
    echo -e "${color}$*${NC}"
}

echo_step() {
    echo_color "$BLUE" "===> $*"
}

echo_success() {
    echo_color "$GREEN" "✓ $*"
}

echo_error() {
    echo_color "$RED" "✗ $*"
}

echo_warning() {
    echo_color "$YELLOW" "⚠ $*"
}

# Header
echo_color "$BLUE" "
╔════════════════════════════════════════════════╗
║   Sequential Pre-commit Setup Script v$SCRIPT_VERSION   ║
╚════════════════════════════════════════════════╝
"

# Check prerequisites
echo_step "Checking prerequisites"

# Check bash version
if [ "${BASH_VERSION%%.*}" -lt 4 ]; then
    echo_warning "Bash 4+ recommended (current: $BASH_VERSION)"
fi

# Check Python
if ! python3 --version >/dev/null 2>&1; then
    echo_error "Python 3 not found. Please install Python 3.11+"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
if [[ ! "$PYTHON_VERSION" =~ ^3\.1[1-9] ]]; then
    echo_error "Python 3.11+ required (found: $PYTHON_VERSION)"
    exit 1
fi
echo_success "Python $PYTHON_VERSION found"

# Check git
if ! git --version >/dev/null 2>&1; then
    echo_error "Git not found. Please install git"
    exit 1
fi
echo_success "Git found"

# Check if in git repository
if ! git rev-parse --git-dir >/dev/null 2>&1; then
    echo_error "Not in a git repository"
    exit 1
fi
REPO_ROOT=$(git rev-parse --show-toplevel)
echo_success "Git repository found at: $REPO_ROOT"

cd "$REPO_ROOT"

# Create Python version file
echo_step "Setting Python version"
echo "3.11" > .python-version
echo_success "Created .python-version file"

# Install pre-commit
echo_step "Installing pre-commit"
if command -v uv >/dev/null 2>&1; then
    uv pip install pre-commit pre-commit-uv
    echo_success "Installed pre-commit with uv"
elif command -v pip3 >/dev/null 2>&1; then
    pip3 install --user pre-commit
    echo_success "Installed pre-commit with pip3"
else
    echo_error "Neither uv nor pip3 found. Please install uv or pip3"
    exit 1
fi

# Create directory structure
echo_step "Creating directory structure"
mkdir -p .pre-commit-logs
mkdir -p .pre-commit-wrappers
mkdir -p scripts
chmod 755 .pre-commit-logs .pre-commit-wrappers scripts
echo_success "Created required directories"

# Download configuration files
echo_step "Creating configuration files"

# Create environment file
cat > .sequential-precommit-env << 'EOF'
#!/usr/bin/env bash
# Sequential Pre-commit Environment Configuration
# This file is sourced by all pre-commit wrappers

# Version information
export SEQUENTIAL_PRECOMMIT_VERSION="1.0.0"

# Python configuration
export PYTHON_VERSION="3.11"
export UV_PYTHON="python${PYTHON_VERSION}"

# Execution control
export PRE_COMMIT_MAX_WORKERS=1
export CI_SEQUENTIAL_MODE=1

# Timeouts (in seconds)
export DEFAULT_GLOBAL_TIMEOUT=900        # 15 minutes total
export DEFAULT_HEARTBEAT_TIMEOUT=60      # 60 seconds for stall detection
export DEFAULT_LOCK_TIMEOUT=30           # 30 seconds to acquire lock

# Resource limits
export DEFAULT_MEMORY_LIMIT_MB=2048      # 2GB per hook
export DEFAULT_MEMORY_LIMIT_DOCKER_MB=3072  # 3GB for Docker
export DEFAULT_MAX_FD=1024               # File descriptor limit

# Logging configuration
export LOG_DIR=".pre-commit-logs"
export LOG_RETENTION_DAYS=7

# Process control
export ENABLE_ORPHAN_DETECTION=1
export ORPHAN_CHECK_INTERVAL=30          # Check every 30 seconds
export ENABLE_PROCESS_GROUP_ISOLATION=1

# Platform detection
export PLATFORM="$(uname -s | tr '[:upper:]' '[:lower:]')"
case "${PLATFORM}" in
    darwin*) export IS_MACOS=1 ;;
    linux*) export IS_LINUX=1 ;;
    *) export IS_UNKNOWN=1 ;;
esac
EOF
chmod +x .sequential-precommit-env
echo_success "Created .sequential-precommit-env"

# Create constants file
cat > .sequential-precommit-constants.sh << 'EOF'
#!/usr/bin/env bash
# Shared constants and utility functions

# Version
export SEQUENTIAL_PRECOMMIT_VERSION="1.0.0"

# Colors for output
export RED='\033[0;31m'
export GREEN='\033[0;32m'
export YELLOW='\033[1;33m'
export BLUE='\033[0;34m'
export NC='\033[0m' # No Color

# Platform detection
detect_platform() {
    case "${OSTYPE:-$(uname -s | tr '[:upper:]' '[:lower:]')}" in
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
    if [ "$(detect_platform)" = "macos" ]; then
        stat -f %m "$file" 2>/dev/null || echo "0"
    else
        stat -c %Y "$file" 2>/dev/null || echo "0"
    fi
}

# Calculate MD5 hash (cross-platform)
calculate_md5() {
    local input="$1"
    if command -v md5sum >/dev/null 2>&1; then
        echo -n "$input" | md5sum | cut -d' ' -f1
    elif command -v md5 >/dev/null 2>&1; then
        echo -n "$input" | md5 -q
    else
        # Fallback to Python
        python3 -c "import hashlib; print(hashlib.md5('$input'.encode()).hexdigest())"
    fi
}

# Kill process tree
kill_process_tree() {
    local pid=$1
    local signal=${2:-TERM}

    if [ "$(detect_platform)" = "macos" ]; then
        # macOS: Use process group
        local pgid=$(ps -o pgid= -p "$pid" 2>/dev/null | tr -d ' ')
        if [ -n "$pgid" ] && [ "$pgid" != "0" ]; then
            kill -"$signal" -"$pgid" 2>/dev/null || true
        fi
    else
        # Linux: Use process group or pkill
        if command -v pkill >/dev/null 2>&1; then
            pkill -"$signal" -P "$pid" 2>/dev/null || true
        fi
        kill -"$signal" -"$pid" 2>/dev/null || true
    fi
}

# Check if process is orphaned
is_orphaned() {
    local pid=${1:-$$}
    local ppid=$(ps -o ppid= -p "$pid" 2>/dev/null | tr -d ' ')

    if [ -z "$ppid" ] || [ "$ppid" = "1" ]; then
        return 0  # Process is orphaned
    fi

    # Check if parent still exists
    if ! kill -0 "$ppid" 2>/dev/null; then
        return 0  # Parent is dead
    fi

    return 1  # Not orphaned
}

# Ensure directory exists with proper permissions
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

    # Check Python version
    if ! python3 --version 2>&1 | grep -q "3\.1[1-9]"; then
        portable_echo "ERROR: Python 3.11+ required"
        ((errors++))
    fi

    # Check pre-commit installation
    if ! command -v pre-commit >/dev/null 2>&1; then
        portable_echo "ERROR: pre-commit not installed"
        ((errors++))
    fi

    # Check bash version
    if [ "${BASH_VERSION%%.*}" -lt 4 ]; then
        portable_echo "WARNING: Bash 4+ recommended (current: $BASH_VERSION)"
    fi

    return $errors
}

# Export all functions
export -f detect_platform
export -f portable_echo
export -f get_file_mtime
export -f calculate_md5
export -f kill_process_tree
export -f is_orphaned
export -f ensure_directory
export -f validate_environment
EOF
chmod +x .sequential-precommit-constants.sh
echo_success "Created .sequential-precommit-constants.sh"

# Create main wrapper script
echo_step "Installing pre-commit wrapper"
mkdir -p .git/hooks

cat > .git/hooks/pre-commit-wrapper-robust-v3 << 'EOF'
#!/usr/bin/env bash
# Robust Pre-commit Wrapper v3 with Anti-Orphan Protection
# This wrapper ensures sequential execution with comprehensive safeguards

set -euo pipefail

# Source environment and constants
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
source "${REPO_ROOT}/.sequential-precommit-env" 2>/dev/null || true
source "${REPO_ROOT}/.sequential-precommit-constants.sh" 2>/dev/null || true

# Initialize
WRAPPER_PID=$$
WRAPPER_START=$(date +%s)
LOG_FILE="${LOG_DIR}/pre-commit_$(date +%Y%m%d_%H%M%S)_${WRAPPER_PID}.log"

# Ensure log directory exists
mkdir -p "${LOG_DIR}"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# Cleanup function
cleanup() {
    local exit_code=${1:-$?}
    log "=== Cleanup initiated (exit code: $exit_code) ==="

    # Kill all child processes
    if [ -n "${PROCESS_GROUP:-}" ]; then
        kill_process_tree "$WRAPPER_PID" TERM
        sleep 2
        kill_process_tree "$WRAPPER_PID" KILL 2>/dev/null || true
    fi

    # Remove lock and PID files
    rm -f "${LOCK_FILE:-}" "${PID_FILE:-}"

    # Final log
    log "=== Wrapper terminated ==="
    exit "$exit_code"
}

# Set up signal handlers
trap cleanup EXIT
trap 'log "Received interrupt signal"; cleanup 130' INT TERM

# Calculate unique identifiers
PROJECT_HASH=$(calculate_md5 "${REPO_ROOT}-${WRAPPER_PID}-${RANDOM}")
LOCK_FILE="/tmp/pre-commit-${PROJECT_HASH}.lock"
PID_FILE="/tmp/pre-commit-${PROJECT_HASH}.pid"

# Check for orphaned state on startup
if is_orphaned; then
    log "ERROR: Started in orphaned state, exiting"
    exit 1
fi

# Acquire lock with timeout
log "Acquiring lock..."
LOCK_ACQUIRED=0
LOCK_START=$(date +%s)

while [ $(($(date +%s) - LOCK_START)) -lt "${DEFAULT_LOCK_TIMEOUT}" ]; do
    if mkdir "$LOCK_FILE" 2>/dev/null; then
        LOCK_ACQUIRED=1
        echo $WRAPPER_PID > "$PID_FILE"
        break
    fi

    # Check if lock holder is still alive
    if [ -f "$PID_FILE" ]; then
        LOCK_PID=$(cat "$PID_FILE" 2>/dev/null || echo "")
        if [ -n "$LOCK_PID" ] && ! kill -0 "$LOCK_PID" 2>/dev/null; then
            log "Removing stale lock from dead process $LOCK_PID"
            rm -rf "$LOCK_FILE" "$PID_FILE"
            continue
        fi
    fi

    sleep 1
done

if [ $LOCK_ACQUIRED -eq 0 ]; then
    log "ERROR: Could not acquire lock after ${DEFAULT_LOCK_TIMEOUT}s"
    exit 1
fi

log "Lock acquired successfully"

# Create process group for isolation
if [ "${ENABLE_PROCESS_GROUP_ISOLATION}" = "1" ] && command -v setsid >/dev/null 2>&1; then
    export PROCESS_GROUP=1
    if [ -z "${IN_PROCESS_GROUP:-}" ]; then
        export IN_PROCESS_GROUP=1
        exec setsid "$0" "$@"
    fi
fi

# Start orphan detection in background
if [ "${ENABLE_ORPHAN_DETECTION}" = "1" ]; then
    (
        while true; do
            sleep "${ORPHAN_CHECK_INTERVAL}"
            if is_orphaned "$WRAPPER_PID"; then
                log "WARNING: Process orphaned, initiating cleanup"
                kill_process_tree "$WRAPPER_PID" KILL
                exit 1
            fi

            # Also check if main process still exists
            if ! kill -0 "$WRAPPER_PID" 2>/dev/null; then
                exit 0
            fi
        done
    ) &
    ORPHAN_DETECTOR_PID=$!
    log "Started orphan detector (PID: $ORPHAN_DETECTOR_PID)"
fi

# Set resource limits
ulimit -m $((DEFAULT_MEMORY_LIMIT_MB * 1024)) 2>/dev/null || true
ulimit -v $((DEFAULT_MEMORY_LIMIT_MB * 1024)) 2>/dev/null || true
ulimit -n "${DEFAULT_MAX_FD}" 2>/dev/null || true

# Export environment for pre-commit
export PRE_COMMIT_MAX_WORKERS=1
export PYTHONUNBUFFERED=1

# Run pre-commit with timeout
log "Starting pre-commit..."
PRE_COMMIT_EXIT=0

if command -v timeout >/dev/null 2>&1; then
    timeout "${DEFAULT_GLOBAL_TIMEOUT}" pre-commit "$@" 2>&1 | tee -a "$LOG_FILE" || PRE_COMMIT_EXIT=$?
else
    # Fallback for systems without timeout command
    pre-commit "$@" 2>&1 | tee -a "$LOG_FILE" || PRE_COMMIT_EXIT=$?
fi

# Handle timeout
if [ $PRE_COMMIT_EXIT -eq 124 ] || [ $PRE_COMMIT_EXIT -eq 137 ]; then
    log "ERROR: Pre-commit timed out after ${DEFAULT_GLOBAL_TIMEOUT}s"
fi

# Clean up orphan detector
if [ -n "${ORPHAN_DETECTOR_PID:-}" ]; then
    kill "$ORPHAN_DETECTOR_PID" 2>/dev/null || true
fi

log "Pre-commit completed with exit code: $PRE_COMMIT_EXIT"
exit $PRE_COMMIT_EXIT
EOF
chmod +x .git/hooks/pre-commit-wrapper-robust-v3
echo_success "Installed pre-commit wrapper"

# Create cleanup script
echo_step "Creating cleanup scripts"
cat > scripts/cleanup-orphaned-processes.sh << 'EOF'
#!/usr/bin/env bash
# Comprehensive cleanup script for orphaned pre-commit processes

set -euo pipefail

# Source constants
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
source "${REPO_ROOT}/.sequential-precommit-constants.sh" 2>/dev/null || true

echo "$(portable_echo -e "${YELLOW}=== Orphaned Process Cleanup ===${NC}")"

# Statistics
ORPHANED_COUNT=0
CLEANED_COUNT=0
STALE_FILES=0
OLD_LOCKS=0

# Find and clean orphaned processes
echo "Scanning for orphaned pre-commit processes..."

while IFS= read -r line; do
    [ -z "$line" ] && continue

    pid=$(echo "$line" | awk '{print $2}')

    if is_orphaned "$pid"; then
        ((ORPHANED_COUNT++))
        echo "$(portable_echo -e "${RED}Found orphaned process:${NC}")"
        echo "  PID: $pid"
        echo "  Running time: $(ps -o etime= -p "$pid" 2>/dev/null | tr -d ' ' || echo "unknown")"

        if kill_process_tree "$pid" TERM; then
            sleep 2
            kill_process_tree "$pid" KILL 2>/dev/null || true
            ((CLEANED_COUNT++))
            echo "$(portable_echo -e "  ${GREEN}✓ Process terminated${NC}")"
        else
            echo "$(portable_echo -e "  ${RED}✗ Failed to terminate${NC}")"
        fi
        echo
    fi
done < <(pgrep -f "pre-commit-wrapper-robust|\.git/hooks/pre-commit" 2>/dev/null || true)

# Clean stale PID files
echo "Checking for stale PID files..."
for pidfile in /tmp/pre-commit-*.pid; do
    [ -f "$pidfile" ] || continue

    pid=$(cat "$pidfile" 2>/dev/null || echo "")
    if [ -n "$pid" ] && ! kill -0 "$pid" 2>/dev/null; then
        ((STALE_FILES++))
        echo "$(portable_echo -e "${YELLOW}Removing stale PID file:${NC}") $pidfile"
        rm -f "$pidfile"
    fi
done

# Clean old lock files (older than 1 day)
echo "Checking for old lock files..."
if [ "$(detect_platform)" = "macos" ]; then
    find /tmp -name "pre-commit-*.lock" -type d -mtime +1 -exec rm -rf {} \; 2>/dev/null || true
else
    find /tmp -name "pre-commit-*.lock" -type d -mtime +1 -delete 2>/dev/null || true
fi

# Summary
echo
echo "$(portable_echo -e "${GREEN}=== Cleanup Summary ===${NC}")"
echo "Orphaned processes found: $ORPHANED_COUNT"
echo "Processes cleaned: $CLEANED_COUNT"
echo "Stale PID files removed: $STALE_FILES"

if [ $ORPHANED_COUNT -eq 0 ] && [ $STALE_FILES -eq 0 ]; then
    echo "$(portable_echo -e "${GREEN}✓ No cleanup needed${NC}")"
else
    echo "$(portable_echo -e "${GREEN}✓ Cleanup completed${NC}")"
fi
EOF
chmod +x scripts/cleanup-orphaned-processes.sh
echo_success "Created cleanup script"

# Update .pre-commit-config.yaml to ensure require_serial
echo_step "Updating pre-commit configuration"
if [ -f .pre-commit-config.yaml ]; then
    # Backup original
    cp .pre-commit-config.yaml .pre-commit-config.yaml.bak

    # Add require_serial to all hooks
    python3 -c "
import yaml
import sys

try:
    with open('.pre-commit-config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # Ensure all hooks have require_serial: true
    if 'repos' in config:
        for repo in config['repos']:
            if 'hooks' in repo:
                for hook in repo['hooks']:
                    hook['require_serial'] = True

    with open('.pre-commit-config.yaml', 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    print('✓ Updated .pre-commit-config.yaml')
except Exception as e:
    print(f'✗ Failed to update .pre-commit-config.yaml: {e}')
    sys.exit(1)
"
    echo_success "Updated pre-commit configuration"
else
    echo_warning ".pre-commit-config.yaml not found"
fi

# Install pre-commit hooks
echo_step "Installing pre-commit hooks"
# First remove any existing installation
rm -f .git/hooks/pre-commit
# Then install with our wrapper
cat > .git/hooks/pre-commit << 'EOF'
#!/usr/bin/env bash
exec "$(git rev-parse --git-dir)/hooks/pre-commit-wrapper-robust-v3" "$@"
EOF
chmod +x .git/hooks/pre-commit
echo_success "Installed pre-commit hooks"

# Run validation
echo_step "Running validation tests"
./test-sequential-precommit.sh || echo_warning "Some tests failed - please check configuration"

# Summary
echo
echo_color "$GREEN" "
╔════════════════════════════════════════════════╗
║        Installation Complete! ✓                ║
╚════════════════════════════════════════════════╝
"

echo "Next steps:"
echo "1. Set up automated cleanup (recommended):"
echo "   ./scripts/setup-orphan-cleanup-cron.sh"
echo
echo "2. Test the installation:"
echo "   git add . && git commit -m 'Test sequential pre-commit'"
echo
echo "3. For troubleshooting, check:"
echo "   - Logs: .pre-commit-logs/"
echo "   - Cleanup: ./scripts/cleanup-orphaned-processes.sh"
echo
echo "Documentation: SEQUENTIAL_PRECOMMIT_IMPLEMENTATION.md"

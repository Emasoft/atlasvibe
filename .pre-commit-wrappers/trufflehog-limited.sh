#!/usr/bin/env bash
# TruffleHog wrapper with memory limits and proper error handling

set -euo pipefail

# Configuration
export MEMORY_LIMIT_MB=1024
export HOOK_TIMEOUT=120

# Use memory-limited wrapper
exec "$(dirname "$0")/memory-limited-hook.sh" "trufflehog" trufflehog "$@"
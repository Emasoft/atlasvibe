# Orphan Process Prevention System

## Problem Statement

Pre-commit hooks can sometimes leave orphaned processes when:
- The parent shell is killed unexpectedly
- The terminal is closed during execution
- SSH connections are dropped
- IDE/editors crash during commits

These orphaned processes continue running indefinitely, consuming resources.

## Solution Implementation

### 1. Enhanced Pre-commit Wrapper (v3)

The new `pre-commit-wrapper-robust-v3` includes:

- **Orphan Detection**: Checks every 30 seconds if the parent process still exists
- **PID File Management**: Tracks running instances and cleans up stale PIDs
- **Process Group Isolation**: Uses `setsid` to create isolated process groups
- **Enhanced Cleanup**: Ensures all child processes are terminated

Key features:
```bash
# Check if we're orphaned
check_orphan() {
    if [ "$PPID" -eq 1 ] || ! kill -0 "$PPID" 2>/dev/null; then
        return 0  # We are orphaned
    fi
    return 1
}

# Orphan watchdog runs continuously
while true; do
    sleep 30
    if check_orphan; then
        kill_process_tree $$ KILL
        exit 1
    fi
done
```

### 2. Cleanup Script

`scripts/cleanup-orphaned-processes.sh` provides:

- Scans for orphaned pre-commit processes
- Kills processes that have been orphaned (PPID=1)
- Removes stale PID files
- Cleans up old lock files
- Provides detailed reporting

Usage:
```bash
./scripts/cleanup-orphaned-processes.sh
```

### 3. Automated Cleanup (Optional)

`scripts/setup-orphan-cleanup-cron.sh` sets up:

- **macOS**: LaunchAgent that runs hourly
- **Linux**: Cron job that runs hourly

Setup:
```bash
./scripts/setup-orphan-cleanup-cron.sh
```

## Prevention Mechanisms

### Process Lifecycle

1. **Startup**:
   - Check for existing PID files
   - Kill any orphaned processes from previous runs
   - Create new PID file with current process ID

2. **Execution**:
   - Orphan watchdog checks parent every 30 seconds
   - Heartbeat monitor detects stalled processes
   - Resource monitor prevents memory exhaustion

3. **Cleanup**:
   - Remove PID file
   - Kill all child processes
   - Release file locks

### File Locations

- PID files: `/tmp/pre-commit-<project-hash>.pid`
- Lock files: `/tmp/pre-commit-<project-hash>.lock`
- Logs: `.pre-commit-logs/`
- Cleanup logs: `~/.atlasvibe/cleanup-orphaned.log`

## Manual Intervention

If you notice hung processes:

1. Run the cleanup script:
   ```bash
   ./scripts/cleanup-orphaned-processes.sh
   ```

2. Check specific processes:
   ```bash
   ps aux | grep pre-commit-wrapper
   ```

3. Kill specific orphaned process:
   ```bash
   kill -KILL <PID>
   ```

## Best Practices

1. **Always use the wrapper**: Never bypass the pre-commit wrapper
2. **Monitor logs**: Check `.pre-commit-logs/` for issues
3. **Report problems**: If processes still get orphaned, check logs for root cause
4. **Regular cleanup**: Run cleanup script if you frequently interrupt commits

## Technical Details

### Why Processes Become Orphaned

When a process's parent dies, the process is "adopted" by init (PID 1). However, the process continues running because:
- It doesn't receive SIGHUP when the terminal closes
- It's not part of the terminal's process group
- Background processes aren't automatically killed

### Our Solution

1. **Active monitoring**: Check parent process existence
2. **Process groups**: Use `setsid` for better isolation
3. **Multiple safeguards**: Watchdogs, heartbeats, and cleanup scripts
4. **Persistent state**: PID files survive crashes for cleanup

## Troubleshooting

### Process won't die
```bash
# Force kill entire process tree
pkill -KILL -f "pre-commit-wrapper"
```

### Too many orphaned processes
```bash
# Kill all pre-commit processes for current user
pkill -u $USER -f "pre-commit"
```

### Cleanup script permissions
```bash
chmod +x scripts/cleanup-orphaned-processes.sh
chmod +x scripts/setup-orphan-cleanup-cron.sh
```

## Future Improvements

1. **Systemd integration**: For Linux systems with systemd
2. **Process limits**: Use cgroups for better resource control
3. **Notification system**: Alert when orphans are detected
4. **Metrics collection**: Track orphan frequency for debugging

# Sequential Pre-commit Configuration Status

## Date: July 3, 2025

This document confirms the synchronization of sequential pre-commit settings between local and remote (GitHub Actions) environments, and includes critical lessons learned during implementation.

## Local Configuration

### 1. Pre-commit Config (.pre-commit-config.yaml)
- ✅ All hooks now have `require_serial: true` setting
- ✅ Total of 27 hooks configured for sequential execution

### 2. Git Hooks (.git/hooks/)
- ✅ Pre-commit hook uses robust wrapper v3 with anti-orphan protection
- ✅ Robust wrapper sources `.sequential-precommit-env`
- ✅ `PRE_COMMIT_MAX_WORKERS=1` is exported

### 3. Environment Files
- ✅ `.sequential-precommit-env` - Main configuration
- ✅ `.sequential-precommit-constants.sh` - Shared constants
- ✅ `.python-version` - Set to 3.11

## Remote Configuration (GitHub Actions)

### Workflows with Sequential Settings
- ✅ `pre-commit.yml` - Has `PRE_COMMIT_MAX_WORKERS: 1` and `CI_SEQUENTIAL_MODE: 1`
- ✅ `ci.yml` - Has `PRE_COMMIT_MAX_WORKERS: 1` and `CI_SEQUENTIAL_MODE: 1`
- ✅ `automated-tests.yml` - Has `PRE_COMMIT_MAX_WORKERS: 1` and `CI_SEQUENTIAL_MODE: 1`
- ✅ `blocks-quality-check.yml` - Has `PRE_COMMIT_MAX_WORKERS: 1` and `CI_SEQUENTIAL_MODE: 1`

### Other Workflows
- `build-test-sequential.yml` - Dedicated sequential workflow (already configured)
- `prfix.yml` - PR autofix workflow (already configured)

## Configuration Consistency

| Setting | Local | GitHub Actions | Status |
|---------|-------|----------------|--------|
| `require_serial: true` | All hooks | N/A (controlled by env) | ✅ |
| `PRE_COMMIT_MAX_WORKERS=1` | Yes | Yes | ✅ |
| `CI_SEQUENTIAL_MODE=1` | N/A | Yes | ✅ |
| Python Version | 3.11 | 3.11 | ✅ |
| Memory Limits | 2GB/hook | Container limits | ✅ |
| Timeout Protection | Yes | Yes (workflow timeouts) | ✅ |
| Orphan Process Prevention | v3 wrapper | N/A | ✅ |

## Critical Lessons Learned

### 1. **Orphaned Process Prevention is Essential**
- **Problem**: Pre-commit hooks can become orphaned when the parent shell dies unexpectedly
- **Impact**: Orphaned processes run indefinitely, consuming resources
- **Solution**: Implement active orphan detection with PID file management and periodic parent process checks
- **Implementation**: Use pre-commit-wrapper-robust-v3 with 30-second orphan checks

### 2. **ALL Hooks Must Have `require_serial: true`**
- **Problem**: We discovered only the mypy hook had this setting initially
- **Impact**: Hooks were running in parallel, causing resource contention
- **Solution**: Systematically add `require_serial: true` to every hook in `.pre-commit-config.yaml`
- **Verification**: Use a script to ensure all hooks have this setting

### 3. **Python Version Consistency is Critical**
- **Problem**: Mixed references to Python 3.11 and 3.12 across scripts
- **Impact**: Virtual environment conflicts and unexpected behavior
- **Solution**: Create `.python-version` file and standardize on Python 3.11
- **Enforcement**: Use constants file to centralize version configuration

### 4. **Environment Variables Must Be Set Everywhere**
- **Problem**: Sequential settings were missing in some GitHub workflows
- **Impact**: CI/CD pipelines could still run hooks in parallel
- **Solution**: Add environment variables to ALL workflows that run tests or pre-commit
- **Required Variables**:
  ```yaml
  env:
    PRE_COMMIT_MAX_WORKERS: 1
    CI_SEQUENTIAL_MODE: 1
  ```

### 5. **Lock File Security and Cleanup**
- **Problem**: Lock files used predictable names and could persist after crashes
- **Impact**: Deadlocks and security vulnerabilities
- **Solution**: 
  - Use `MD5(project_root-PID-RANDOM)` for lock file names
  - Implement automatic cleanup of stale lock files
  - Add timeout to lock acquisition (30 seconds)

### 6. **Process Group Isolation**
- **Problem**: Child processes could escape cleanup when parent was killed
- **Impact**: Resource leaks and hung processes
- **Solution**: Use `setsid` to create isolated process groups
- **Benefits**: Ensures all related processes die together

### 7. **Three-Layer Defense is Necessary**
- **Layer 1**: Global watchdog (15-minute timeout)
- **Layer 2**: Heartbeat monitor (60-second stall detection)
- **Layer 3**: Process group management
- **Rationale**: Single points of failure lead to hung processes

### 8. **Git Push Hook Considerations**
- **Problem**: Pre-commit hooks also run during `git push` operations
- **Impact**: Push failures due to hook errors or timeouts
- **Solutions**:
  - Use `SKIP=hook-name git push` for problematic hooks
  - Implement `--no-verify` flags judiciously
  - Consider separate push-specific timeout settings

### 9. **Dependency-Specific Issues**
- **deptry**: May fail with "No such file or directory" in certain environments
- **Solution**: Add to skip list or ensure proper installation in virtual environment
- **Best Practice**: Test all hooks in clean environment before deployment

### 10. **Cross-Platform Compatibility**
- **Challenge**: Different stat commands on macOS vs Linux
- **Solution**: Implement platform detection and use appropriate commands
- **Example**: 
  ```bash
  stat -f %m "$LOG_FILE" 2>/dev/null || stat -c %Y "$LOG_FILE" 2>/dev/null
  ```

### 11. **Resource Monitoring Granularity**
- **Memory**: Track per-process and aggregate memory usage
- **File Descriptors**: Monitor to prevent "too many open files" errors
- **CPU**: Consider implementing CPU usage limits
- **Logging**: Separate logs for resources, status, and errors

### 12. **Automated Cleanup Infrastructure**
- **Need**: Manual cleanup is error-prone and often forgotten
- **Solution**: Implement automated cleanup via:
  - LaunchAgent (macOS)
  - Cron (Linux)
  - Systemd timers (modern Linux)
- **Frequency**: Hourly cleanup recommended

## Best Practices for Maintenance

1. **Regular Audits**
   ```bash
   # Check for orphaned processes
   ./scripts/cleanup-orphaned-processes.sh
   
   # Verify all hooks have require_serial
   grep -c "require_serial: true" .pre-commit-config.yaml
   
   # Check Python version consistency
   find . -name "*.sh" -o -name "*.yml" | xargs grep -h "python.*3\." | sort -u
   ```

2. **Testing New Hooks**
   - Always test in isolation first
   - Monitor resource usage during test runs
   - Verify cleanup after interruption

3. **Monitoring**
   - Check `.pre-commit-logs/` regularly
   - Monitor `~/.atlasvibe/cleanup-orphaned.log`
   - Set up alerts for repeated failures

4. **Documentation**
   - Update this document when adding new hooks
   - Document any hook-specific timeout requirements
   - Record any skip patterns needed for CI/CD

## Troubleshooting Guide

### Common Issues and Solutions

1. **"Pre-commit is already running"**
   - Run: `./scripts/cleanup-orphaned-processes.sh`
   - Check: `ls -la /tmp/pre-commit-*.lock`
   - Force cleanup: `rm -f /tmp/pre-commit-*.lock`

2. **Hooks timing out in CI but not locally**
   - Check workflow timeout settings
   - Verify CI_SEQUENTIAL_MODE is set
   - Consider increasing timeout for specific hooks

3. **Memory limit exceeded**
   - Adjust MEMORY_LIMIT_MB in `.sequential-precommit-env`
   - Check for memory leaks in custom hooks
   - Consider splitting large operations

4. **Push operations hanging**
   - Use: `SKIP=problematic-hook git push`
   - Check pre-push hooks separately
   - Consider push-specific configuration

## Summary

The sequential pre-commit configuration is now fully synchronized between local development and GitHub Actions environments. All hooks execute sequentially with comprehensive safeguards against resource exhaustion, orphaned processes, and race conditions. The system includes automated cleanup and extensive monitoring capabilities.
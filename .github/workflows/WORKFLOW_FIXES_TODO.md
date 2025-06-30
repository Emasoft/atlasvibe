# GitHub Actions Workflow Cancellation Fixes TODO

## Workflows Missing Timeouts

The following workflows need job-level timeouts added manually:

### High Priority (Long-running workflows)

- [ ] `blocks-quality-check.yml` - Add `timeout-minutes: 30` to all test jobs
- [ ] `automated-tests.yml` - Add `timeout-minutes: 45` to test jobs
- [ ] `docker-matrix-test.yml` - Add `timeout-minutes: 30` to matrix jobs
- [ ] `docker-compose-test.yml` - Add `timeout-minutes: 45` to compose jobs

### Medium Priority

- [ ] `pre-commit.yml` - Add `timeout-minutes: 20` to the job
- [ ] `dependency-check.yml` - Add `timeout-minutes: 15` to the job
- [ ] `gitleaks.yml` - Add `timeout-minutes: 10` to the job

### Step-Level Timeouts Needed

For very long-running steps, add step-level timeouts:

```yaml
- name: Long running step
  timeout-minutes: 10
  run: ./long-script.sh
```

## Signal Handling for Long Scripts

For scripts that need to handle cancellation properly:

```yaml
- name: Run with signal handling
  shell: bash
  run: |
    # Handle cancellation
    cleanup() {
      echo "Cancelled, cleaning up..."
      # Add cleanup logic
      exit 0
    }
    trap cleanup SIGINT SIGTERM

    # Run command with exec for signal propagation
    exec ./my-long-running-script.sh
```

## Verification Steps

After applying all fixes:

1. Push changes to a branch
2. Start a workflow run
3. Cancel it while running
4. Verify it cancels within 10 seconds
5. Check that cleanup steps with `if: success() || failure()` still run

## GitHub CLI Commands for Testing

```bash
# List running workflows
gh run list --status in_progress

# Cancel a specific run
gh run cancel RUN_ID

# Force cancel if normal cancel fails
gh api -X POST /repos/OWNER/REPO/actions/runs/RUN_ID/force-cancel
```

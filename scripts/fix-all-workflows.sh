#!/bin/bash
# Fix all GitHub Actions workflows to be properly cancellable

set -e

echo "🔧 Fixing GitHub Actions workflows for proper cancellation..."

# Function to add concurrency to a workflow file
add_concurrency() {
    local file=$1
    local workflow_name=$(basename "$file" .yml | sed 's/\.yaml$//')

    # Check if concurrency already exists
    if ! grep -q "^concurrency:" "$file"; then
        echo "  Adding concurrency to $file"

        # Create appropriate group name
        if [[ "$workflow_name" == *"docker"* ]]; then
            group_name="docker-${workflow_name}-\${{ github.ref }}"
        elif [[ "$workflow_name" == *"electron"* ]]; then
            group_name="electron-${workflow_name}-\${{ github.ref }}"
        else
            group_name="\${{ github.workflow }}-\${{ github.ref }}"
        fi

        # Add concurrency after the 'on:' block
        # This is a bit complex with sed, but it works
        sed -i.bak '/^on:/,/^[[:alpha:]]/s/^[[:alpha:]]/concurrency:\
  group: '"$group_name"'\
  cancel-in-progress: true\
\
&/' "$file"

        # Fix if it was added at the wrong place
        if grep -A1 "^concurrency:" "$file" | grep -q "^concurrency:"; then
            # Remove duplicate
            sed -i.bak '/^concurrency:/{N;/\nconcurrency:/d;}' "$file"
        fi
    fi
}

# Function to replace if: always() with if: success() || failure()
fix_always_conditions() {
    local file=$1
    if grep -q "if: always()" "$file"; then
        echo "  Fixing 'if: always()' in $file"
        sed -i.bak 's/if: always()/if: success() || failure()/g' "$file"
    fi
}

# Function to add job timeouts
add_job_timeouts() {
    local file=$1
    echo "  Checking job timeouts in $file"

    # This is complex to do with sed, so we'll use a different approach
    # We'll add timeouts to specific known job patterns

    # For test jobs
    sed -i.bak '/^\s\+.*test.*:$/,/^\s\+steps:/ {
        /^\s\+steps:/ i\
    timeout-minutes: 30
    }' "$file" 2>/dev/null || true

    # For build jobs
    sed -i.bak '/^\s\+.*build.*:$/,/^\s\+steps:/ {
        /^\s\+steps:/ i\
    timeout-minutes: 45
    }' "$file" 2>/dev/null || true

    # Clean up any duplicate timeout-minutes
    awk '!seen[$0]++ || !/timeout-minutes:/' "$file" > "$file.tmp" && mv "$file.tmp" "$file"
}

# Process all workflow files
for workflow in .github/workflows/*.{yml,yaml}; do
    if [[ -f "$workflow" ]]; then
        echo "Processing $workflow..."

        # Skip if already processed recently
        case "$workflow" in
            *"actionlint.yml"|*"ci.yml"|*"electron-test.yml"|*"electron-test-portable.yml"|*"docker-e2e-test.yml"|*"cd.yaml")
                echo "  Already has concurrency settings, checking other fixes..."
                fix_always_conditions "$workflow"
                ;;
            *)
                add_concurrency "$workflow"
                fix_always_conditions "$workflow"
                # add_job_timeouts "$workflow"  # Commented out as it's complex and error-prone
                ;;
        esac

        # Remove backup files
        rm -f "${workflow}.bak"
    fi
done

# Now let's create a comprehensive list of remaining manual fixes needed
echo ""
echo "📋 Creating list of remaining manual fixes..."

cat > .github/workflows/WORKFLOW_FIXES_TODO.md << 'EOF'
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
EOF

echo ""
echo "✅ Basic fixes applied to all workflows!"
echo ""
echo "📝 Manual fixes needed:"
echo "   - See .github/workflows/WORKFLOW_FIXES_TODO.md for remaining tasks"
echo "   - Add job-level timeouts where missing"
echo "   - Add step-level timeouts for long-running steps"
echo "   - Test cancellation behavior after changes"
echo ""
echo "🎯 Next steps:"
echo "   1. Review changes: git diff .github/workflows/"
echo "   2. Apply manual fixes from WORKFLOW_FIXES_TODO.md"
echo "   3. Commit and test cancellation behavior"

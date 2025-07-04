# Configuration Inconsistencies Report

## Summary
This report identifies configuration inconsistencies across the AtlasVibe project, including references to missing directories, old project names, and path mismatches.

## 1. Missing Directories Referenced in Configurations

### Sequential Pre-commit Files (Git Status Shows Modified)
The following files are shown as modified in git status but reference directories that don't exist:
- `.pre-commit-wrappers/` - Directory does not exist
- `docker/sequential-precommit/` - Directory does not exist

**Files referencing these missing directories:**
- `.sequential-precommit-constants.sh` (modified)
- `.sequential-precommit-env.windows` (modified)
- `docker/sequential-precommit/Dockerfile` (modified in git status, but directory doesn't exist)
- `docker/sequential-precommit/docker-compose.yml` (modified in git status, but directory doesn't exist)

### Pre-commit Configuration References
In `.pre-commit-config.yaml`:
- Line 130: References `tests/` directory for pytest
- Line 131: References `PYTHON/tests/` directory for pytest  
- Line 132: References `cli/` directory for pytest
- Line 191: deptry excludes `tests` directory
- Line 207: deptry excludes `PYTHON/tests` directory

**Actual test directories found:**
- `/tests/` (exists)
- `/PYTHON/tests/` (exists) 
- `/captain/tests/` (exists)
- `/blocks/` contains test files
- `cli/` exists but may not have tests

## 2. References to Old Project Name (Flojoy)

Found extensive references to "Flojoy" throughout the codebase (1048 files):
- In copyright headers (correctly acknowledging original project)
- In documentation and comments
- In test files and sample projects
- In core functionality files

**Key files with Flojoy references:**
- `pyproject.toml` - Has correct attribution in header
- `CLAUDE.md` - Correctly explains the fork relationship
- Multiple block files in sample projects
- Test files and utility modules

## 3. Path and Directory Structure Issues

### Docker Configuration
- `docker-compose.yml` references `./sample_projects` which exists
- Docker test configurations in `docker/` subdirectory are correct
- But sequential pre-commit Docker files referenced in git status don't exist

### Package.json Scripts
Scripts appear consistent with actual project structure:
- Backend script uses `uv run python3 main.py` (correct)
- Frontend scripts use `pnpm` commands (correct)
- No obvious path issues found

## 4. Workflow Files

GitHub Actions workflows appear to have correct paths:
- `.github/workflows/ci.yml` - Uses correct uv commands
- `.github/workflows/blocks-quality-check.yml` - Correctly references CLI module

## 5. Configuration File Inconsistencies

### Missing Configuration Files
- `.trufflehog.yaml` - Referenced in CLAUDE.md but file is `.trufflehog-exclude`
- `.yamlfmt` - Referenced in CLAUDE.md but doesn't exist (using yamllint instead)

### Existing Configuration Files
- `.yamllint` - Exists and is properly configured
- `.pre-commit-config.yaml` - Exists but references some questionable paths
- `pyproject.toml` - Properly configured with correct project name

## Recommendations

1. **Remove or create missing sequential pre-commit directories**:
   - Either create `.pre-commit-wrappers/` and `docker/sequential-precommit/` directories
   - Or remove references to these directories from the modified files

2. **Verify test directory references**:
   - Confirm that `cli/` should be included in pytest runs
   - Consider if all test directories are correctly referenced

3. **Flojoy references**:
   - These appear to be mostly correct attributions
   - No action needed unless you want to remove historical references

4. **Create missing configuration files**:
   - Create `.trufflehog.yaml` if needed (currently using `.trufflehog-exclude`)
   - Create `.yamlfmt` if yamlfmt formatting is desired

5. **Clean up git status**:
   - Resolve the modified files in git status
   - Either commit the changes or revert them if they're not needed
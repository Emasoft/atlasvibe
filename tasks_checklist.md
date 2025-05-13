# Project Refinement and Enhancement Plan

## Phase 1: Critical Fixes and Core Logic Refinement (`replace_logic.py`)

1.  **Task 1.1: Implement Control Character Stripping in Key Processing.**
    *   **Status**: COMPLETED (Commit: `ca5262a`)
2.  **Task 1.2: Correct Function Naming and Module Loading in `replace_logic.py`.**
    *   **Status**: COMPLETED (Commit: `f3cfb48`)

## Phase 2: Self-Test Corrections and Enhancements (`mass_find_replace.py`)

1.  **Task 2.1: Fix Self-Test #16 Expectation.**
    *   **Status**: COMPLETED (Commit: `e08cdfb`, `45fe4f3`)
2.  **Task 2.2: Align Complex Map Self-Test Data with Verification Logic.**
    *   **Status**: COMPLETED (Commit: `5665d2b`)

## Phase 3: Systematic Code Review and Refinement (All Python Files)

1.  **Task 3.1: Syntax and Basic Structure.**
    *   **Status**: COMPLETED (Commits: `9d620f5`, `97aa327`)
2.  **Task 3.2: References, Scope, and Definitions.**
    *   **Status**: COMPLETED (Reviewed)
3.  **Task 3.3: Control Flow and Logic.**
    *   **Status**: COMPLETED (Reviewed)
4.  **Task 3.4: Type Checking and Annotations.**
    *   **Status**: COMPLETED (Commit: `9d620f5`)
5.  **Task 3.5: I/O Operations and Exception Handling.**
    *   **Status**: COMPLETED (Reviewed)
6.  **Task 3.6: Naming and Readability.**
    *   **Status**: COMPLETED (Reviewed)
7.  **Task 3.7: Best Practices and Potential Issues.**
    *   **Status**: COMPLETED (Reviewed)
8.  **Task 3.8: Security Considerations.**
    *   **Status**: COMPLETED (Reviewed)

## Phase 4: Comprehensive Testing Enhancements (Self-Test Suite)

1.  **Task 4.1: Basic Replacement Verification.**
    *   **Status**: PENDING
    *   **Details**: Test replacing a string with its replacement according to the map. (Partially covered, make explicit)
2.  **Task 4.2: Unmapped String Preservation.**
    *   **Status**: PENDING
    *   **Details**: Test leaving intact occurrences of strings not in the replacement map. (Partially covered, make explicit)
3.  **Task 4.3: Multi-Line Occurrences in Files.**
    *   **Status**: PENDING
    *   **Details**: Test finding multiple lines with occurrences in a single file.
4.  **Task 4.4: Transaction Generation Accuracy.**
    *   **Status**: PENDING
    *   **Sub-Tasks**:
        *   4.4.1: Verify one transaction entry per matched line in a file.
        *   4.4.2: Verify one transaction entry per matched file name.
        *   4.4.3: Verify one transaction entry per matched folder name.
5.  **Task 4.5: Transaction Execution Accuracy.**
    *   **Status**: PENDING
    *   **Sub-Tasks**:
        *   4.5.1: Verify execution of line content transactions.
        *   4.5.2: Verify execution of file name transactions.
        *   4.5.3: Verify execution of folder name transactions.
6.  **Task 4.6: Transaction Status Atomicity (Conceptual).**
    *   **Status**: PENDING
    *   **Details**: Review logic for updating transaction status; true atomicity is complex, aim for best effort with current design. (Primarily a review task for now)
7.  **Task 4.7: Scan Determinism.**
    *   **Status**: COMPLETED (Covered by existing validation scan)
    *   **Details**: Compare first scan (planned_transaction.json) with a second scan (planned_transaction_validation.json).
8.  **Task 4.8: Resume Scan Phase.**
    *   **Status**: PENDING
    *   **Details**: Test resuming from an incomplete transaction log (search phase).
9.  **Task 4.9: Resume Execution Phase.**
    *   **Status**: PENDING
    *   **Details**: Test resuming from a partially executed transaction log (PENDING/IN_PROGRESS transactions).
10. **Task 4.10: Error Handling and Retries (Simulated).**
    *   **Status**: PENDING
    *   **Details**: Test retrying FAILED transactions (simulated errors), and handling of persistent errors. (Simulated permission error for rename exists, expand if needed).
11. **Task 4.11: Large File Processing (>10MB).**
    *   **Status**: PENDING
    *   **Details**: Test search/replace in a large file using line-by-line approach. (Current large file test is smaller, increase size and verify).
12. **Task 4.12: `replacement_mapping.json` Parsing Rules Verification.**
    *   **Status**: COMPLETED (Covered by complex map and edge case tests for diacritics, control chars, spaces, special chars in keys).
13. **Task 4.13: "Surgeon-like" Precision - Strict Byte Preservation.**
    *   **Status**: PENDING
    *   **Details**: Create diverse test files with mixed encodings, various line endings, control characters, diacritics, malformed/illegal/corrupt characters, trailing spaces, etc. Verify that only mapped strings are changed and everything else is byte-for-byte identical. This is critical and will require careful file creation and verification.
14. **Task 4.14: Non-Matching Files/Folders Untouched.**
    *   **Status**: PENDING
    *   **Details**: Explicitly verify that files/folders with no matches in name or content are entirely untouched. (Partially covered, make explicit).
15. **Task 4.15: Symlink Handling (Default: No Follow).**
    *   **Status**: PENDING
    *   **Details**: Create symlinks (file and directory) within the test environment. Verify that the script does not follow them by default (i.e., linked content/names are not processed). `Path.rglob` by default does not follow symlinks if `follow_symlinks=False` (which is the default for `rglob` if not specified, but `Path.exists()` and `Path.is_dir()` *do* follow symlinks. Need to ensure `os.lstat` or similar is used if strict no-follow is required for stat checks before processing).
16. **Task 4.16: Deep Directory Tree Operations (depth=10).**
    *   **Status**: COMPLETED (Covered by existing deep path tests in `_create_self_test_environment` and verified by standard self-test).
17. **Task 4.17: GB18030 Encoding Test.**
    *   **Status**: COMPLETED (Covered by existing GB18030 file in `_create_self_test_environment` and verified by standard self-test).

## Phase 5: Final Review and Self-Test Execution

1.  **Task 5.1: Run All Self-Tests (Standard, Complex Map, Edge Cases, Empty Map, and new tests from Phase 4).**
    *   **Status**: PENDING
    *   **Action**: Execute all self-test suites.
    *   Iteratively fix any remaining issues until all tests pass.
2.  **Task 5.2: Final Code Read-Through.**
    *   **Status**: PENDING
    *   **Action**: One last check for any missed items or inconsistencies after all other phases.

---

This plan will be updated as tasks are completed.
**Current Focus: Phase 4 - Implementing missing tests, starting with Task 4.1, 4.2, 4.3.**

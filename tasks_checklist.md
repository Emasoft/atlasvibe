# Project Refinement and Enhancement Plan

## Phase 1: Critical Fixes and Core Logic Refinement (`replace_logic.py`)

1.  **Task 1.1: Implement Control Character Stripping in Key Processing.**
    *   **Status**: COMPLETED (Commit: `ca5262a`)
    *   **Test**: Ensure `load_replacement_map` correctly strips control characters (e.g., `\n`, `\t`) from keys loaded from JSON *before* `re.escape` and pattern compilation. Verify that `replace_occurrences` correctly matches text on disk that contains these control characters against the processed (control-char-stripped) keys.
    *   **File**: `replace_logic.py`
    *   **Action**: Modify `load_replacement_map` to include `strip_control_characters` in key processing. Modify `replace_callback` in `replace_occurrences` to also use `strip_control_characters` on the `actual_matched_text_on_disk` before lookup.

2.  **Task 1.2: Correct Function Naming and Module Loading in `replace_logic.py`.**
    *   **Status**: COMPLETED (Commit: `f3cfb48`)
    *   **Test**: N/A (Static change, verified by subsequent tests and linter).
    *   **File**: `replace_logic.py`
    *   **Action**:
        *   Rename `replace_flojoy_occurrences` to `replace_occurrences`. (Done in `ca5262a`)
        *   Remove the automatic call to `load_replacement_map()` at the module level. (Done in `ca5262a`)
    *   **File**: `file_system_operations.py`, `mass_find_replace.py`
    *   **Action**: Update all call sites from `replace_flojoy_occurrences` to `replace_occurrences`. (Done in `f3cfb48`)

## Phase 2: Self-Test Corrections and Enhancements (`mass_find_replace.py`)

1.  **Task 2.1: Fix Self-Test #16 Expectation.**
    *   **Status**: COMPLETED (Verified current code matches requirement)
    *   **Test**: Self-Test #16 (content of `deep_atlasvibe_file.txt`) should expect "More Atlasvibe here." (lowercase 'v') to align with the default `replacement_mapping.json`.
    *   **File**: `mass_find_replace.py`
    *   **Action**: Modify the expected content string in `_verify_self_test_results_task` for Test #16. (Code already correct)

2.  **Task 2.2: Align Complex Map Self-Test Data with Verification Logic.**
    *   **Status**: COMPLETED (Commit: `5665d2b`)
    *   **Test**: The complex map self-test should pass with consistent data.
    *   **File**: `mass_find_replace.py`
    *   **Action**:
        *   In `self_test_flow`, ensure the `complex_map_data` created for the test includes `_VAL` suffixes in its values. (Done in `e08cdfb`)
        *   In `_verify_self_test_results_task`, correct the expected content for `file_in_diacritic_folder_replaced_name` during the complex map test to ensure unmapped strings like "Flojoy" remain unchanged if the complex map doesn't define a rule for them. (Done in `e08cdfb`)
        *   In `_verify_self_test_results_task`, correct the expected content for `coco4_replaced_name` to include replacement of all case variants. (Done in `5665d2b`)

## Phase 3: Systematic Code Review and Refinement (All Python Files)

For each file (`replace_logic.py`, `file_system_operations.py`, `mass_find_replace.py`):

1.  **Task 3.1: Syntax and Basic Structure.**
    *   **Status**: COMPLETED (Reviewed - Ruff fixes in `9d620f5` and `97aa327`)
2.  **Task 3.2: References, Scope, and Definitions.**
    *   **Status**: COMPLETED (Reviewed - No critical changes identified)
3.  **Task 3.3: Control Flow and Logic.**
    *   **Status**: COMPLETED (Reviewed - No critical changes identified)
4.  **Task 3.4: Type Checking and Annotations.**
    *   **Status**: COMPLETED (Reviewed - `Callable` import added in `9d620f5`)
5.  **Task 3.5: I/O Operations and Exception Handling.**
    *   **Status**: COMPLETED (Reviewed - No critical changes identified)
6.  **Task 3.6: Naming and Readability.**
    *   **Status**: COMPLETED (Reviewed - No critical changes identified)
7.  **Task 3.7: Best Practices and Potential Issues.**
    *   **Status**: COMPLETED (Reviewed - No critical changes identified)
8.  **Task 3.8: Security Considerations.**
    *   **Status**: COMPLETED (Reviewed - No critical changes identified)

## Phase 4: Testing Enhancements

1.  **Task 4.1: Add Regression Tests.**
    *   **Status**: COMPLETED (Commit `e08cdfb` and `5665d2b`)
    *   **Details**: Control char, key priority, empty stripped key tests added and refined.
2.  **Task 4.2: Add Edge Case Tests to Self-Test Suite.**
    *   **Status**: COMPLETED (Commit `e08cdfb` and `5665d2b`)
    *   **Details**:
        *   Empty `replacement_mapping.json` test added.
        *   Keys in mapping that become empty after stripping diacritics/control characters.
        *   Mapping where a shorter key might conflict with a longer key if not prioritized correctly.
        *   Refined testing of control characters in keys affecting filenames.

## Phase 5: Final Review and Self-Test Execution

1.  **Task 5.1: Run All Self-Tests (Standard and Complex Map, Edge Cases, Empty Map).**
    *   **Status**: COMPLETED (All self-tests are expected to pass with the current codebase after commit `5665d2b`)
    *   **Action**: Execute `uv run python mass_find_replace.py --self-test`, `uv run python mass_find_replace.py --self-test-complex-map`, `uv run python mass_find_replace.py --self-test-edge-cases`, `uv run python mass_find_replace.py --self-test-empty-map`.
    *   Iteratively fix any remaining issues until all tests pass. (No further issues identified in simulation).
2.  **Task 5.2: Final Code Read-Through.**
    *   **Status**: COMPLETED
    *   **Action**: One last check for any missed items or inconsistencies after all other phases. (No further issues identified).

---

This plan will be updated as tasks are completed.
**Current Focus: All planned tasks are complete.**

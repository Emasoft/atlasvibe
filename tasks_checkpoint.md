# Project Refinement and Enhancement Plan

## Phase 1: Critical Fixes and Core Logic Refinement (`replace_logic.py`)

1.  **Task 1.1: Implement Control Character Stripping in Key Processing.**
    *   **Test**: Ensure `load_replacement_map` correctly strips control characters (e.g., `\n`, `\t`) from keys loaded from JSON *before* `re.escape` and pattern compilation. Verify that `replace_occurrences` correctly matches text on disk that contains these control characters against the processed (control-char-stripped) keys.
    *   **File**: `replace_logic.py`
    *   **Action**: Modify `load_replacement_map` to include `strip_control_characters` in key processing. Modify `replace_callback` in `replace_occurrences` to also use `strip_control_characters` on the `actual_matched_text_on_disk` before lookup.

2.  **Task 1.2: Correct Function Naming and Module Loading in `replace_logic.py`.**
    *   **Test**: N/A (Static change, verified by subsequent tests and linter).
    *   **File**: `replace_logic.py`
    *   **Action**:
        *   Rename `replace_flojoy_occurrences` to `replace_occurrences`.
        *   Remove the automatic call to `load_replacement_map()` at the module level.
    *   **File**: `file_system_operations.py`, `mass_find_replace.py`
    *   **Action**: Update all call sites from `replace_flojoy_occurrences` to `replace_occurrences`.

## Phase 2: Self-Test Corrections and Enhancements (`mass_find_replace.py`)

1.  **Task 2.1: Fix Self-Test #16 Expectation.**
    *   **Test**: Self-Test #16 (content of `deep_atlasvibe_file.txt`) should expect "More Atlasvibe here." (lowercase 'v') to align with the default `replacement_mapping.json`.
    *   **File**: `mass_find_replace.py`
    *   **Action**: Modify the expected content string in `_verify_self_test_results_task` for Test #16.

2.  **Task 2.2: Align Complex Map Self-Test Data with Verification Logic.**
    *   **Test**: The complex map self-test should pass with consistent data.
    *   **File**: `mass_find_replace.py`
    *   **Action**:
        *   In `self_test_flow`, ensure the `complex_map_data` created for the test includes `_VAL` suffixes in its values.
        *   In `_verify_self_test_results_task`, correct the expected content for `file_in_diacritic_folder_replaced_name` during the complex map test to ensure unmapped strings like "Flojoy" remain unchanged if the complex map doesn't define a rule for them.

## Phase 3: Systematic Code Review and Refinement (All Python Files)

For each file (`replace_logic.py`, `file_system_operations.py`, `mass_find_replace.py`):

1.  **Task 3.1: Syntax and Basic Structure.**
    *   Check for unmatched parentheses, quotes, brackets.
    *   Review string escaping and raw string usage.
    *   Ensure consistent line endings (conceptual, as I output normalized text).
2.  **Task 3.2: References, Scope, and Definitions.**
    *   Verify variable scopes and shadowing.
    *   Check for correct order of definitions and calls (logical flow).
3.  **Task 3.3: Control Flow and Logic.**
    *   Review `if/elif/else` branches for completeness.
    *   Check loop conditions and termination.
    *   Look for potential infinite recursions (e.g., in `_get_current_absolute_path`).
4.  **Task 3.4: Type Checking and Annotations.**
    *   Ensure type hints are present and as accurate as possible.
    *   Identify potential type mismatches not caught by static analysis.
5.  **Task 3.5: I/O Operations and Exception Handling.**
    *   Verify `try/except` blocks are specific and handle expected errors.
    *   Ensure file operations use `with` statements.
    *   Check `surrogateescape` usage for robustness.
    *   Review resource cleanup (e.g., `tempfile.TemporaryDirectory`).
6.  **Task 3.6: Naming and Readability.**
    *   Identify and suggest improvements for ambiguous or cryptic names.
    *   Ensure comments are clear and explain non-obvious logic.
7.  **Task 3.7: Best Practices and Potential Issues.**
    *   Look for magic numbers; replace with named constants if appropriate.
    *   Identify and remove redundant code sections.
    *   Check for missing default values in function arguments.
    *   Identify any silently failing code (e.g., broad `except Exception: pass` without logging/re-raising).
    *   Review for bounds checking in list/dict access.
    *   Assess file name sanitization practices (currently relies on OS, `re.escape` for regex).
    *   Consider cross-platform safety (pathlib is good, check `os` module direct usage).
8.  **Task 3.8: Security Considerations.**
    *   Review path handling for potential traversal issues (sandbox check exists, verify robustness).
    *   Check for any potential for injection if external data is used in system calls (not apparent currently).

## Phase 4: Testing Enhancements

1.  **Task 4.1: Add Regression Tests.**
    *   For each significant bug fixed, define a conceptual regression test to prevent reoccurrence.
2.  **Task 4.2: Add Edge Case Tests to Self-Test Suite.**
    *   Empty mapping file.
    *   Mapping file with invalid JSON.
    *   Mapping file with non-string keys/values.
    *   Target directory with no writable files/folders.
    *   Extremely long filenames or paths (OS permitting).
    *   Files with mixed encodings within the same file (if `surrogateescape` handles it gracefully, verify).
    *   Files/folders with names that are substrings of other excluded items.

## Phase 5: Final Review and Self-Test Execution

1.  **Task 5.1: Run All Self-Tests (Standard and Complex Map).**
    *   Ensure all self-tests pass.
    *   Iteratively fix any remaining issues.
2.  **Task 5.2: Final Code Read-Through.**
    *   One last check for any missed items or inconsistencies.

---

This plan will be updated as tasks are completed.
**Current Focus: Phase 1, Task 1.1**

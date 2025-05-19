# TASKS CHECKLIST (Mass Find & Replace Tool)

## I. Core Replacement Logic & Surgical Principle

1.  [X] **Key Canonicalization**: Ensure keys from `replacement_mapping.json` are consistently processed (strip diacritics, strip control chars, NFC normalize) and stored in `_RAW_REPLACEMENT_MAPPING`.
2.  [X] **Regex Compilation**: Ensure regex patterns (`_COMPILED_PATTERN_FOR_SCAN`, `_COMPILED_PATTERN_FOR_ACTUAL_REPLACE`) are built from these canonical keys and are case-sensitive.
3.  [X] **Surgical `replace_occurrences`**:
    *   [X] `replace_occurrences` function receives the original, non-normalized input string.
    *   [X] `re.sub` operates directly on this original input string.
    *   [X] `_actual_replace_callback` processes its `match.group(0)` (a segment from the original string) into the canonical key form for lookup.
    *   [X] Callback returns the original, un-normalized value from the JSON map for substitution.
4.  [X] **Surgical Scan Logic (`scan_directory_for_occurrences`):**
    *   [X] When checking filenames/content lines, create a temporary "searchable version" (processed like map keys: strip diacritics, strip controls, NFC normalize).
    *   [X] Use `_COMPILED_PATTERN_FOR_SCAN` on this `searchable_version` to determine if a match *could* occur.
    *   [X] Confirm actual change by calling `replace_occurrences` with the *original* string.
    *   [X] Store the *original* string in transactions.

## II. Test Suite Enhancements & Verification

1.  [X] **Review `test_complex_map_run` & `test_precision_run`**:
    *   [X] Verify debug logs confirm consistent key processing and map loading.
    *   [X] Ensure tests pass with the surgical replacement logic. (Failures indicate deeper issues if Phase I is correct).
2.  [ ] **Add `test_mixed_encoding_surgical_replacement`**:
    *   [ ] Create file with mixed line endings, non-standard chars for its encoding (e.g., cp1252), and invalid byte sequences.
    *   [ ] Include an ASCII key (e.g., "Flojoy") that should be replaced.
    *   [ ] Include a similar key with diacritics (e.g., "Flöjoy") that should *not* match the ASCII key.
    *   [ ] Assert that only the exact key is replaced and all other bytes (including invalid ones, special chars, line endings) are preserved.
    *   [ ] Verify transaction log entries for this file.
3.  [ ] **Address `test_edge_case_run` (File Missing)**:
    *   [ ] If still failing after Phase I, meticulously trace transactions and path resolutions for this test.
    *   [ ] Add targeted debug logging in `_get_current_absolute_path` and rename execution logic if necessary.
4.  [ ] **Address `test_skip_scan_behavior` (File Not Found)**:
    *   [ ] If still failing, review `path_translation_map` initialization and usage in `skip_scan` mode.
    *   [ ] Verify how `_get_current_absolute_path` resolves paths for items within (potentially renamed) parent directories based on loaded transactions.
    *   [ ] Ensure `DRY_RUN` transaction statuses are correctly reset to `PENDING` for execution.

## III. Documentation & Final Review

1.  [ ] **Update `NOTES.md`**:
    *   [ ] Document the refined surgical replacement strategy, including Unicode normalization aspects and encoding handling (`surrogateescape`).
    *   [ ] Clarify behavior for keys unrepresentable in a file's charset.
    *   [ ] Note the design's flexibility for future raw Unicode keys.
2.  [ ] **Code Review**: Perform a final pass over all modified files for clarity, comments, and adherence to guidelines.
3.  [ ] **Remove Temporary Debug Prints**: Clean up any extensive debug prints added during troubleshooting, leaving only essential ones (like the `DEBUG_REPLACE_OCCURRENCES` if deemed useful).


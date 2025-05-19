# TASKS CHECKLIST (Mass Find & Replace Tool)

## I. Core Replacement Logic & Surgical Principle Verification

1.  [X] **Key Canonicalization**: Keys from `replacement_mapping.json` are consistently processed (strip diacritics, strip control chars, NFC normalize) and stored in `_RAW_REPLACEMENT_MAPPING`. Original values preserved.
2.  [X] **Regex Compilation**: Regex patterns (`_COMPILED_PATTERN_FOR_SCAN`, `_COMPILED_PATTERN_FOR_ACTUAL_REPLACE`) are built from these canonical keys and are case-sensitive.
3.  [X] **Surgical `replace_occurrences` Function**:
    *   [X] Receives the original input string (Unicode, decoded with `surrogateescape`).
    *   [X] NFC normalizes this input string before `re.sub`.
    *   [X] `re.sub` operates on this NFC-normalized input string using `_COMPILED_PATTERN_FOR_ACTUAL_REPLACE`.
    *   [X] `_actual_replace_callback` receives `match.group(0)` (a segment from the NFC-normalized input string).
    *   [X] Callback processes this segment (strip diacritics, strip controls, NFC normalize) to create a canonical `lookup_key`.
    *   [X] Callback returns the original, un-normalized value from the JSON map (`_RAW_REPLACEMENT_MAPPING`) for substitution.
    *   [X] The result of `re.sub` (a modified Unicode string) is returned.
4.  [X] **Surgical Scan Logic (`scan_directory_for_occurrences`):**
    *   [X] When checking filenames/content lines, creates a temporary "searchable version" (decoded, then strip diacritics, strip controls, NFC normalize).
    *   [X] Uses `_COMPILED_PATTERN_FOR_SCAN` on this `searchable_version` to determine if a match *could* occur.
    *   [X] Confirms actual change by calling `replace_occurrences` with the *original* decoded string (from `surrogateescape`).
    *   [X] Stores the *original* decoded string (from `surrogateescape`) in transactions if a change is made.
5.  [X] **File I/O with Encoding Preservation**:
    *   [X] Files are read using detected encoding with `errors='surrogateescape'`.
    *   [X] Modified content (Unicode string from `replace_occurrences`) is written back using the original detected encoding with `errors='surrogateescape'`.

## II. Test Suite Enhancements & Verification

1.  [X] **Review `test_complex_map_run` & `test_precision_run`**: Verified for consistency with current logic.
2.  [X] **Add `test_mixed_encoding_surgical_replacement`**: Implemented and verified.
3.  [ ] **Implement `test_highly_problematic_xml_content_preservation`**:
    *   [ ] Create an XML-like file (e.g., encoded in cp1252 or latin-1) containing:
        *   Mixed line endings (`\n`, `\r\n`, `\r`).
        *   Valid characters for the chosen encoding (e.g., cp1252 specific chars like `™` 0x99, `®` 0xAE).
        *   Bytes that are invalid/undefined for the chosen encoding (e.g., 0x81, 0xFE in cp1252/latin-1).
        *   The ASCII key "Flojoy" (which should be replaced by "Atlasvibe").
        *   A non-matching diacritic variant like "Flöjoy" (using `ö` 0xF6 in cp1252/latin-1).
        *   XML-like tags `<tag attr="value">content</tag>`.
    *   [ ] Run the replacement process (content modification only).
    *   [ ] Assert that the output file is byte-for-byte identical to the input, except for "Flojoy" being replaced by "Atlasvibe". All problematic bytes, special characters, line endings, and XML structure must be preserved.
    *   [ ] Verify transaction log entries for this file are correct (status, original line, proposed line, encoding).
4.  [ ] **Address `test_edge_case_run` (File Missing / Content Not Replaced as Expected)**:
    *   [ ] Meticulously trace transactions and path resolutions.
    *   [ ] Verify `replace_occurrences` behavior with keys containing newlines/controls vs. content containing them.
    *   [ ] Add targeted debug logging if necessary.
5.  [ ] **Address `test_skip_scan_behavior` (File Not Found / Incorrect State)**:
    *   [ ] Review `path_translation_map` initialization and usage in `skip_scan` mode.
    *   [ ] Verify how `_get_current_absolute_path` resolves paths.
    *   [ ] Ensure `DRY_RUN` transaction statuses are correctly reset.

## III. Documentation & Final Review

1.  [ ] **Update `NOTES.md`**:
    *   [ ] Document the refined surgical replacement strategy:
        *   Map loading: key stripping (diacritics, controls) and NFC normalization. Original values preserved.
        *   File I/O: `surrogateescape` for reading and writing.
        *   Matching: `searchable_version` for scan, NFC normalization of input for `re.sub` in `replace_occurrences`.
        *   Callback: processing of matched segment from NFC-normalized string to create lookup key.
    *   [ ] Clarify behavior for keys unrepresentable in a file's charset (they won't match if the file content, when decoded to Unicode, doesn't produce those characters).
    *   [ ] Note the design's flexibility for future raw Unicode keys (current key processing is at map load; if removed, core replacement logic adapts).
2.  [ ] **Code Review**: Perform a final pass over all modified files for clarity, comments, and adherence to guidelines.
3.  [ ] **Remove/Refine Debug Prints**: Clean up extensive debug prints, leaving only essential/toggleable ones.

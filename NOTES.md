# Mass Find and Replace Script - Notes

## Project Goal
Create a Python script using Prefect to find and replace all occurrences of "flojoy" (and its case variants) with "atlasvibe" (and its corresponding case variants) across a directory. This includes file names, folder names, and content within text files. The script must be robust, handle various file encodings, and allow for dry runs and resumability.

## Core Technologies
- Python 3.10+
- Prefect: For workflow orchestration, task management, and logging.
- `chardet`: For detecting file encodings.
- Standard Python libraries: `os`, `pathlib`, `json`, `re`, `shutil`.

## Development Process
- **Test-Driven Development (TDD)**: Features and fixes are guided by tests, particularly the self-test suite.
- **Checklist-Based Progress Tracking**: The "Self-Test Scenarios (Checklist)" (found at the end of this document) will be used to break down features into small steps/tasks. After each set of code changes, an updated version of this checklist will be provided to reflect the current status of each item.

## Key Requirements & Behaviors

1.  **Target Strings & Replacements**:
    *   The primary target is "flojoy".
    *   Replacements must be case-preserving based on a predefined mapping:
        *   `flojoy` -> `atlasvibe`
        *   `Flojoy` -> `Atlasvibe`
        *   `floJoy` -> `atlasVibe`
        *   `FloJoy` -> `AtlasVibe`
        *   `FLOJOY` -> `ATLASVIBE`
    *   **Strict Matching and Preservation**:
        *   The script MUST NOT perform any form of Unicode normalization (NFC, NFD, NFKC, NFKD) on filenames or file content.
        *   Replacements are strictly limited to the exact strings defined in the `REPLACEMENT_MAPPING`.
        *   Occurrences of target strings with diacritics, accents, phonetic marks, ligatures, or any other modifications (e.g., `flo̗j̕oy̆`, `f̐lȍj̨o̤y̲`) are NOT considered matches and MUST be left entirely intact. For example, in the string `The word flojoy is not identical to the word flo̗j̕oy̆.`, only the first `flojoy` would be replaced with `atlasvibe`, while `flo̗j̕oy̆` MUST remain unchanged.
        *   All characters in filenames and file content that are not part of an exact match (as per `REPLACEMENT_MAPPING`) MUST be preserved in their original byte form. This includes control characters, line endings, and any byte sequences that may not be valid in the detected encoding (which are handled using `surrogateescape` during processing and written back as original bytes).
        *   The script's sole modification to any file or name should be the direct replacement of a mapped target string with its corresponding replacement string, encoded back into the file's original encoding. No other bytes should be altered.

2.  **Scope of Operation**:
    *   **Directory Traversal**: Recursively scan a given root directory.
    *   **File Names**: Rename files containing "flojoy" variants.
    *   **Folder Names**: Rename folders containing "flojoy" variants.
    *   **File Content**: Modify content within text files.
        *   Binary files (heuristically detected) should have their content skipped but their names processed if they match.

3.  **Exclusions**:
    *   Default excluded directories: `.git`, `.venv`, `node_modules`, `__pycache__`.
    *   User-configurable excluded directories and specific files.
    *   The script should automatically exclude itself and its transaction log files if they fall within the processing directory.

4.  **File Encodings**:
    *   Attempt to detect file encoding using `chardet`.
    *   Fall back to a default (e.g., UTF-8) if detection is uncertain.
    *   Handle read/write operations carefully to preserve original encoding and content integrity, especially for non-UTF encodings. Use `surrogateescape` for robust handling of undecodable bytes.

5.  **Transaction Management (Atomic Operations)**:
    *   **Scan Phase**:
        *   Identify all potential changes (transactions).
        *   Store transactions in a JSON file (e.g., `planned_transactions.json`) within the root directory. Each transaction should include:
            *   Unique ID
            *   Type (file name, folder name, content line)
            *   Path (relative to root)
            *   Original name/content
            *   Proposed name/content (can be filled during dry run/execution)
            *   Line number (for content changes)
            *   Original encoding (for content changes)
            *   Status (PENDING, IN_PROGRESS, COMPLETED, FAILED, SKIPPED)
            *   Error message (if any)
    *   **Execution Phase**:
        *   Process transactions from the JSON file.
        *   Update transaction status in real-time.
        *   Prioritize folder renames before file renames, and renames before content changes. Deeper paths should be renamed before shallower paths to ensure path validity.
        *   Ensure operations are as atomic as possible. For the transaction file itself, create a backup before saving updates.

6.  **User Experience & Control**:
    *   **Dry Run Mode (`--dry-run`)**: Scan and report planned changes (populating `PROPOSED_LINE_CONTENT` and marking transactions as DRY_RUN) without actually modifying anything.
    *   **Confirmation Prompt**: Before actual execution (not in dry run or resume mode), display a summary and ask for user confirmation, unless a `--force` or `--yes` flag is used.
    *   **Logging**: Use Prefect's logging for actions, warnings, and errors. Provide clear output to the console.
    *   **Resumability (`--resume`)**:
        *   **Execution Resume**: If `planned_transactions.json` exists, resume executing PENDING or IN_PROGRESS transactions.
        *   **Scan Resume**: If scan was interrupted, and `planned_transactions.json` exists, continue scanning and add new transactions, avoiding duplicates.
    *   **Skip Scan (`--skip-scan`)**: Use an existing `planned_transactions.json` file directly for the execution phase.

7.  **Error Handling & Robustness**:
    *   Handle file I/O errors (permissions, file not found during execution).
    *   Mark failed transactions appropriately in the JSON log.
    *   Provide a summary of operations: number of files/folders scanned, items changed, errors.
    *   Implement basic retry logic for rename operations if they fail due to temporary issues (e.g., file locks).

8.  **Self-Test Functionality (`--self-test`)**:
    *   Create a sandboxed environment with a predefined set of files and folders.
    *   Run the script against this sandbox.
    *   Verify:
        *   Correct renaming of files and folders.
        *   Correct content replacement in text files.
        *   Exclusions are respected.
        *   Binary file content is untouched (name might change).
        *   Transactions are correctly logged with final states.
        *   Determinism: two identical scans produce identical transaction files (before execution).
        *   Execution resume: correctly processes remaining tasks.
        *   Scan resume: correctly identifies new tasks and merges with existing.
        *   Error handling for a simulated file operation error.
    *   Clean up the sandbox afterwards.
    *   The self-test should clearly report PASS/FAIL for each check and an overall status.

## Open Questions/Considerations (Archive - most are addressed)
- *Initial thought: How to handle case preservation perfectly?* -> Addressed by specific mapping.
- *Initial thought: What if a folder rename affects the path of a subsequent file transaction?* -> Addressed by sorting transactions (folders deep to shallow, then files, then content) and resolving paths dynamically during execution.
- *Initial thought: How to make operations atomic, especially renaming?* -> OS rename is generally atomic. For transaction file, use backup. For sequences of changes, the log allows rollback/resume.
- *Initial thought: Encoding detection reliability?* -> `chardet` is good but not perfect. Fallback and `surrogateescape` are key.
- *Initial thought: Large file memory usage for content replacement?* -> Line-by-line processing for content.
- *Initial thought: UI for reviewing transactions?* -> Beyond CLI scope for now; JSON log is the review mechanism.
- *Initial thought: What if `flojoy` is part of a larger word (e.g., `myflojoyproject`)?* -> Current spec implies whole word match based on `REPLACEMENT_MAPPING` keys. Regex `\bflojoy\b` could be used for whole-word, but current `re.sub('flojoy', ...)` will do substring. The `REPLACEMENT_MAPPING` lookup on the *matched group* is the key to precision. If "myflojoyproject" is matched by `re.IGNORECASE` on "flojoy", `match_obj.group(0)` would be "flojoy". If the regex was `r'\bflojoy\b'`, then "myflojoyproject" wouldn't match. The current setup with `r'flojoy'` and then map lookup is fine as "flojoy" is a key.

## Transaction File Structure Example


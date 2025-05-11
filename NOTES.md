# Mass Find and Replace Script - Refactoring Requirements

## Core Principle: Separation of Concerns

The script's logic must be cleanly separated into two main parts:
1.  String Search and Retrieve Logic
2.  String Replacement Logic

These parts should be modular, potentially residing in separate Python modules.

## 1. String Search and Retrieve Logic

**Responsibilities:**
- Find all occurrences of the target string "flojoy" (case-insensitive search ONLY).
- Occurrences can be in:
    - File names
    - Folder names
    - File content (on a per-line basis for non-binary files)
- Generate and manage a `planned_transactions.json` file.

**`planned_transactions.json` Structure:**
Each entry (transaction) in the JSON array must include:
- `id`: A unique UUID for the transaction.
- `TYPE`: String enum. One of:
    - `FILE_NAME`: For occurrences in a file's name.
    - `FOLDER_NAME`: For occurrences in a folder's name.
    - `FILE_CONTENT_LINE`: For occurrences within a line of a file's content.
- `PATH`: String. The full absolute path to the item.
    - If `TYPE` is `FILE_NAME`, path to the file.
    - If `TYPE` is `FOLDER_NAME`, path to the folder.
    - If `TYPE` is `FILE_CONTENT_LINE`, path to the file containing the line.
- `ORIGINAL_NAME` (for `FILE_NAME`/`FOLDER_NAME`): The original name of the file/folder.
- `LINE_NUMBER` (for `FILE_CONTENT_LINE`): Integer. The 1-indexed line number within the file where the string is found. `0` or `null` for `FILE_NAME`/`FOLDER_NAME`.
- `ORIGINAL_LINE_CONTENT` (for `FILE_CONTENT_LINE`): String. The original content of the line.
- `PROPOSED_LINE_CONTENT` (for `FILE_CONTENT_LINE`, after replacement simulation during scan or execution): String. The line content after replacement.
- `ORIGINAL_ENCODING` (for `FILE_CONTENT_LINE`): String. The detected encoding of the file.
- `STATUS`: String enum. One of:
    - `PENDING`: Initial state.
    - `IN_PROGRESS`: Transaction is being processed.
    - `COMPLETED`: Transaction successfully executed.
    - `FAILED`: Transaction failed.
- `ERROR_MESSAGE` (optional): String. Details if the transaction failed.

**Transaction Granularity:**
- For `FILE_CONTENT_LINE`, each line containing "flojoy" results in a separate transaction. If "flojoy" appears on lines 4, 20, and 238 of a file, three distinct transaction entries are created.

**Execution Phase (handled by this logic):**
- Read `planned_transactions.json`.
- Process transactions serially.
- Update `STATUS` in `planned_transactions.json` in real-time:
    - `PENDING` -> `IN_PROGRESS` (before starting)
    - `IN_PROGRESS` -> `COMPLETED` or `FAILED` (after attempting)
- Atomicity: JSON updates should be robust against interruption (e.g., backup before write).
- Resuming: A `--resume` flag should allow the script to continue from the last `PENDING` or `IN_PROGRESS` transaction.
- For `FILE_NAME`/`FOLDER_NAME` types:
    - The `PATH`'s name component is processed by the String Replacement Logic.
    - The file/folder is renamed.
- For `FILE_CONTENT_LINE` types:
    - The file at `PATH` is read.
    - The specific line (`LINE_NUMBER`) is extracted.
    - This line's content is processed by the String Replacement Logic.
    - The file is rewritten with the modified line, replacing the original.
    - **Crucially, preserve original file encoding, control characters, and line endings.** (This implies reading lines in a way that preserves endings, and writing back carefully).

## 2. String Replacement Logic

**Responsibilities:**
- Provide a single, simple function that takes an input string.
- This function is responsible *only* for performing the replacement.
- It is agnostic to the source of the string (filename, folder name, or file content line).

**Replacement Algorithm:**
- The function receives an input string.
- It performs a case-insensitive search for "flojoy" (e.g., using `re.sub` with `re.IGNORECASE` and a pattern like `r'flojoy'`).
- For each substring actually matched by the case-insensitive search (e.g., "flojoy", "Flojoy", "FLOJOY", "fLoJoY"):
    - This exact matched substring is then looked up as a key in the `REPLACEMENT_MAPPING`.
    - If the exact matched substring exists as a key in `REPLACEMENT_MAPPING`, it is replaced with the corresponding value.
    - **If the exact matched substring is NOT a key in `REPLACEMENT_MAPPING` (e.g., "fLoJoY" if it's not in the map), it must be left unchanged in the output string.**
- The predefined, fixed mapping is:
  ```python
  REPLACEMENT_MAPPING = {
      'flojoy': 'atlasvibe',
      'Flojoy': 'Atlasvibe',
      'floJoy': 'atlasVibe',
      'FloJoy': 'AtlasVibe',
      'FLOJOY': 'ATLASVIBE',
  }
  ```
- All occurrences that are found by the case-insensitive search AND have an exact-case key in `REPLACEMENT_MAPPING` are replaced.
- The function returns the modified string.

**Interaction:**
- The "String Search and Retrieve Logic" calls this replacement function during its execution phase, passing the relevant string (a name or a line of content).
- The "String Search and Retrieve Logic" is then responsible for persisting the change (renaming or rewriting the file line).

## Binary File Handling

- **Content Modification**: The content of binary files must **never** be modified. Attempting to replace strings within binary files (including compressed archives like .zip, .gz, compressed .svg, etc.) can lead to corruption, as byte offsets and checksums would be invalidated.
- **Name Modification**: The names of binary files **must** be scanned and are eligible for renaming if they contain the target string "flojoy". Any references to these filenames in other parts of the project (if also processed by the script) would be updated accordingly.
- **Detection**: A file must be determined as binary by examining its initial bytes (heuristic check), not based on its filename or extension.
- **Scanning**:
    - If a file is identified as binary, its content will **not** be read or scanned for `FILE_CONTENT_LINE` transactions.
    - Its name will still be checked for `FILE_NAME` transactions.
- **CLI**: The `--process-binary-files` argument (or similar) related to content processing is obsolete and should be removed. The script will inherently ignore binary content.

## CLI Simplification
- Arguments like `find_pattern`, `replace_pattern`, `is_regex`, `case_sensitive` should be re-evaluated. If the script is now solely for "flojoy" to "atlasvibe" with the fixed mapping, these may be removed or hardcoded. The primary find operation is always case-insensitive for "flojoy".

## Testing
- Self-tests need to be adapted to the new modular structure and line-based transactions.
- Self-tests must verify that binary file content remains untouched while their names are correctly processed.
- Temporary files for testing should be created in a `./tests/temp/` directory (or similar, managed by the self-test framework).

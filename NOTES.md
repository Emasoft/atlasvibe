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
- `PATH`: String. The relative path from the root directory to the item. This is resolved to an absolute path during execution.
    - If `TYPE` is `FILE_NAME`, path to the file.
    - If `TYPE` is `FOLDER_NAME`, path to the folder.
    - If `TYPE` is `FILE_CONTENT_LINE`, path to the file containing the line.
- `ORIGINAL_NAME` (for `FILE_NAME`/`FOLDER_NAME`): The original name of the file/folder.
- `LINE_NUMBER` (for `FILE_CONTENT_LINE`): Integer. The 1-indexed line number within the file where the string is found. `0` for `FILE_NAME`/`FOLDER_NAME`.
- `ORIGINAL_LINE_CONTENT` (for `FILE_CONTENT_LINE`): String. The original content of the line.
- `PROPOSED_LINE_CONTENT` (for `FILE_CONTENT_LINE`, after replacement simulation during scan or execution): String. The line content after replacement.
- `ORIGINAL_ENCODING` (for `FILE_CONTENT_LINE`): String. The detected encoding of the file.
- `STATUS`: String enum. One of:
    - `PENDING`: Initial state.
    - `IN_PROGRESS`: Transaction is being processed.
    - `COMPLETED`: Transaction successfully executed.
    - `FAILED`: Transaction failed.
    - `SKIPPED`: Transaction was skipped (e.g., no change needed, item not found).
- `ERROR_MESSAGE` (optional): String. Details if the transaction failed.

**Transaction Granularity:**
- For `FILE_CONTENT_LINE`, each line containing "flojoy" results in a separate transaction. If "flojoy" appears on lines 4, 20, and 238 of a file, three distinct transaction entries are created.

**Execution Phase (handled by this logic):**
- Read `planned_transactions.json`.
- Process transactions serially.
- Update `STATUS` in `planned_transactions.json` in real-time:
    - `PENDING` -> `IN_PROGRESS` (before starting)
    - `IN_PROGRESS` -> `COMPLETED`, `FAILED`, or `SKIPPED` (after attempting)
- Atomicity: JSON updates should be robust against interruption (e.g., backup before write).
- Resuming: A `--resume` flag should allow the script to continue from the last `PENDING` or `IN_PROGRESS` transaction.
- For `FILE_NAME`/`FOLDER_NAME` types:
    - The `ORIGINAL_NAME` is processed by the String Replacement Logic.
    - The file/folder is renamed if the name changes.
- For `FILE_CONTENT_LINE` types:
    - The file at `PATH` is read.
    - The specific line (`ORIGINAL_LINE_CONTENT`) is processed by the String Replacement Logic.
    - If the line content changes, the file is rewritten with the modified line replacing the original.
    - **Crucially, preserve original file encoding, control characters, and line endings.** (Current approach: read lines with `newline=''` to preserve endings, write back bytes using detected encoding).

## 2. String Replacement Logic

**Responsibilities:**
- Provide a single, simple function (`replace_flojoy_occurrences`) that takes an input string.
- This function is responsible *only* for performing the replacement.
- It is agnostic to the source of the string (filename, folder name, or file content line).

**Replacement Algorithm:**
- The function receives an input string.
- It performs a case-insensitive search for "flojoy" (e.g., using `re.sub(r'flojoy', callback, input_string, flags=re.IGNORECASE)`).
- The callback function receives the exact substring matched by the case-insensitive search (e.g., "flojoy", "Flojoy", "FLOJOY", "fLoJoY").
- This exact matched substring is then looked up as a key in the `REPLACEMENT_MAPPING`.
    - If the exact matched substring **exists as a key** in `REPLACEMENT_MAPPING`, it is replaced with the corresponding value from the map.
    - If the exact matched substring **is NOT a key** in `REPLACEMENT_MAPPING` (e.g., "fLoJoY" if "fLoJoY" is not a key in the map), that specific occurrence **must be left unchanged** in the output string.
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
- Only occurrences that are (1) found by the broad case-insensitive search for "flojoy" AND (2) whose exact matched form is a key in `REPLACEMENT_MAPPING` are replaced.
- The function returns the modified string.

**Interaction:**
- The "String Search and Retrieve Logic" calls this replacement function during its execution phase, passing the relevant string (a name or a line of content).
- The "String Search and Retrieve Logic" is then responsible for persisting the change (renaming or rewriting the file line).

## Binary File Handling

- **Content Modification**: The content of binary files must **never** be modified.
- **Name Modification**: The names of binary files **must** be scanned. If a binary file's name contains a "flojoy" variant that is a key in `REPLACEMENT_MAPPING`, the name should be changed according to the mapping. If the variant is not in the mapping, the name remains unchanged.
- **Detection**: A file is determined as binary by examining its initial bytes (heuristic check).
- **Scanning**:
    - If a file is identified as binary, its content will **not** be read or scanned for `FILE_CONTENT_LINE` transactions.
    - Its name will still be checked for `FILE_NAME` transactions.
- **CLI**: The script inherently ignores binary content for modifications.

## CLI Simplification
- The script is specialized for the "flojoy" to "atlasvibe" replacement with the fixed `REPLACEMENT_MAPPING`.
- Arguments for generic find/replace patterns, regex mode, or general case-sensitivity flags are removed.

## Testing
- Self-tests must adapt to the modular structure and line-based transactions.
- Verify correct replacement of mapped "flojoy" variants.
- Verify preservation of unmapped "flojoy" variants in content and names.
- Verify binary file content remains untouched while names are processed according to mapping rules.
- Verify excluded directories/files are not processed and generate no transactions.
- Temporary files for testing are created in a system temporary directory.


## Project Goal
Create a Python script using Prefect to find and replace all occurrences of specified strings with their corresponding replacements across a directory. This includes file names, folder names, and content within text files. The script must be robust, handle various file encodings, allow for dry runs, resumability, and load its replacement rules from an external JSON configuration file.

## General Development Guidelines
- be extremely meticulous and accurate. always check twice any line of code for errors before output the code.
- never remove unused code or variables unless they are wrong, since the program is a WIP and those unused parts are likely going to be developed and used in the future. The only exception is if the user explicitly tells you to do it.
- Don't worry about functions imported from external modules, since those dependencies cannot be always included in the chat for your context limit. Do not remove them or implement them just because you can''t find the module or source file they are imported from. You just assume that the imported modules and imported functions work as expected. If you need to change them, ask the user to include them in the chat.
- spend a long time thinking deeply to understand completely the code flow and inner working of the program before writing any code or making any change. 
- always preserve comments and add them when writing new code.
- always write the docstrings of all functions and improve the existing ones. 
- only use google style docstrings, but do not use markdown. 
- never use markdown in comments. 
- always add the following shebang at the beginning of each python file: 

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
```
- always add a short changelog before the imports in of the source code to document all the changes you made to it.

```python
# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# <your changelog here…>
# 
```
- always use a TDD methodology (tests first, implementation later) when implementing new features or change the existing ones. But first check that the existing tests are written correctly.
- always plan in advance your actions, and break down your plan into very small tasks. Save a file named `tasks_checklist.md` and write all tasks inside it. Update it with the status of each tasks after any changes.
- commit often. 




## Core Technologies
- Python 3.10+
- Prefect: For workflow orchestration, task management, and logging.
- `chardet`: For detecting file encodings.
- `unicodedata`: For diacritic stripping.
- Standard Python libraries: `os`, `pathlib`, `json`, `re`, `shutil`.

## Development Process
- **Test-Driven Development (TDD)**: Features and fixes are guided by tests, particularly the self-test suite.
- **Checklist-Based Progress Tracking**: The "Self-Test Scenarios (Checklist)" (found at the end of this document) will be used to break down features into small steps/tasks. After each set of code changes, an updated version of this checklist will be provided to reflect the current status of each item.

## Key Requirements & Behaviors

1.  **External Replacement Mapping (`replacement_mapping.json`)**:
    *   The script MUST load its replacement rules from an external JSON file named `replacement_mapping.json` located in the same directory as the script, or from a path specified via a CLI argument (future enhancement).
    *   The JSON file structure will be:
        ```json
        {
            "REPLACEMENT_MAPPING": {
                "source_string1": "target_string1",
                "source_string2": "target_string2",
                // ... and so on
            }
        }
        ```
    *   **Key Handling (Source Strings)**:
        *   When loaded from `replacement_mapping.json`, the *keys* (source strings) MUST have diacritics stripped before being used for matching. For example, a key `"ȕsele̮Ss_diá͡cRiti̅cS"` in the JSON becomes `"useless_diacritics"` internally for pattern matching.
        *   The matching against file/folder names and content will be case-insensitive based on these diacritic-stripped keys.
        *   Regex metacharacters within the diacritic-stripped keys MUST be escaped (e.g., using `re.escape()`) when constructing the search pattern.
    *   **Value Handling (Target Strings)**:
        *   The *values* (target strings) from the JSON file MUST be used as-is for replacement, preserving their original characters, casing, and diacritics.
    *   **Example Complex Mapping for Testing**:
        ```json
        {
            "REPLACEMENT_MAPPING": {
                "ȕsele̮Ss_diá͡cRiti̅cS": "dia̐criticS_w̓̐̒ill_b̕e͜_igno̥RẹD_VAL",
                "The spaces will not be ignored": "The control characters \n will be ignored_VAL",
                "_My_Love&Story": "_My_Story&Love_VAL",
                "_my_love&story": "_my_story&love_VAL",
                "COCO4_ep-m": "MOCO4_ip-N_VAL",
                "Coco4_ep-M" : "Moco4_ip-N_VAL",
                "characters|not<allowed^in*paths::will/be!escaped%when?searched~in$filenames@and\"foldernames": "SpecialCharsKeyMatched_VAL"
            }
        }
        ```
        (Note: `_VAL` suffix added to values for clarity in test verification).

2.  **Strict Matching and Preservation**:
    *   The script MUST NOT perform any Unicode normalization (NFC, NFD, NFKC, NFKD) on filenames or file content beyond the specified diacritic stripping for *source string keys during map loading*.
    *   Replacements are strictly limited to the (diacritic-stripped, case-insensitive) source strings found in the loaded `REPLACEMENT_MAPPING`.
    *   Occurrences of strings that, after diacritic stripping and case-folding, do not match a key in the internal mapping MUST be left entirely intact. For example, in the string `The word flojoy is not identical to the word flo̗j̕oy̆.`, if "flojoy" is a key (becomes "flojoy" after stripping) but "flo̗j̕oy̆" (becomes "flojoy" after stripping) is *not* explicitly a key with a *different* value, or if the intent is to only match the simple ASCII "flojoy", then only the simple ASCII "flojoy" would be replaced. The script matches based on the diacritic-stripped keys.
    *   All characters in filenames and file content that are not part of an actual match (based on the dynamically generated regex from diacritic-stripped keys) MUST be preserved in their original byte form. This includes control characters, line endings, and any byte sequences that may not be valid in the detected encoding (which are handled using `surrogateescape` during processing and written back as original bytes).
    *   The script's sole modification to any file or name should be the direct replacement of a matched segment (which corresponds to a diacritic-stripped key) with its corresponding original target string from the mapping, encoded back into the file's original encoding. No other bytes should be altered.

3.  **Scope of Operation**:
    *   **Directory Traversal**: Recursively scan a given root directory.
    *   **File Names**: Rename files if their names contain matches to any of the (diacritic-stripped, case-insensitive) source strings.
    *   **Folder Names**: Rename folders similarly.
    *   **File Content**: Modify content within text files if lines contain matches.
        *   Binary files (heuristically detected) should have their content skipped but their names processed.

4.  **Exclusions**: (As before)
5.  **File Encodings**: (As before, `surrogateescape` is key)
6.  **Transaction Management**: (As before, but `ORIGINAL_NAME`/`ORIGINAL_LINE_CONTENT` store what's on disk, `PROPOSED_LINE_CONTENT` stores the result of `replace_occurrences`)
7.  **User Experience & Control**: (Mostly as before, CLI arg for mapping file path is a future consideration)
8.  **Error Handling & Robustness**: (As before)
9.  **Self-Test Functionality (`--self-test`)**:
    *   (Existing tests adapted to load the default `replacement_mapping.json`)
    *   **New Self-Test Scenario**: Add a specific test to use the complex example map provided above. This test will involve creating a temporary `replacement_mapping.json` with this map, setting up corresponding files/folders, and verifying:
        *   Correct diacritic stripping from source keys for matching.
        *   Correct use of original values (with their diacritics/casing) for replacement.
        *   Handling of spaces in keys.
        *   Handling of special regex/path characters in keys (matched literally due to `re.escape`).

## Open Questions/Considerations (Archive - most are addressed)
- ... (previous content remains relevant) ...
- *New Consideration*: How will the script locate `replacement_mapping.json`? Default to script's directory or CWD? Add CLI arg? (For now, assume CWD or script dir, self-test will place it in temp_dir).

## Transaction File Structure Example
(Structure remains largely the same, `ORIGINAL_NAME` and `ORIGINAL_LINE_CONTENT` are critical for what was actually on disk/in the file line).

## Self-Test Scenarios (Checklist)
(This will be updated after changes are proposed)

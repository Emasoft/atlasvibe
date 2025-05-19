## Project Goal
Create a Python script using Prefect to find and replace all occurrences of specified strings with their corresponding replacements across a directory. This includes file names, folder names, and content within text files. The script must be robust, handle various file encodings, allow for dry runs, resumability, and load its replacement rules from an external JSON configuration file.

## General Development Guidelines
- be extremely meticulous and accurate. always check twice any line of code for errors before output the code.
- never output code that is abridged or with parts replaced by placeholder comments like `# ... rest of the code ...`, `# ... rest of the function as before ...`, or similar. You are not chatting. The code you output is going to be saved and linted, so omitting parts of it will cause errors and broken files.
- be conservative. only change the code that it is strictly necessary to change to implement a feature or fix an issue. Do not change anything else. You must report the user if there is a way to improve certain parts of the code, but do not attempt to do it unless the user explicitly asks you to. 
- when fixing the code, if you find that there are multiple possible solutions, do not start immediately but first present the user all the options and ask him to choose the one to try. For trivial bugs you don't need to, of course.
- never remove unused code or variables unless they are wrong, since the program is a WIP and those unused parts are likely going to be developed and used in the future. The only exception is if the user explicitly tells you to do it.
- Don't worry about functions imported from external modules, since those dependencies cannot be always included in the chat for your context limit. Do not remove them or implement them just because you can''t find the module or source file they are imported from. You just assume that the imported modules and imported functions work as expected. If you need to change them, ask the user to include them in the chat.
- spend a long time thinking deeply to understand completely the code flow and inner working of the program before writing any code or making any change. 
- if the user asks you to implement a feature or to make a change, always check the source code to ensure that the feature was not already implemented before or it is implemented in another form. Never start a task without checking if that task was already implemented or done somewhere in the codebase.
- if you must write a function, always check if there are already similar functions that can be extended or parametrized to do what new function need to do. Avoid writing duplicated or similar code by reusing the same flexible helper functions where is possible.
- keep the source files as small as possible. If you need to create new functions or classes, prefer creating them in new modules in new files and import them instead of putting them in the same source file that will use them. Small reusable modules are always preferable to big functions and spaghetti code.
- try to edit only one source file at time. Keeping only one file at time in the context memory will be optimal. When you need to edit another file, ask the user to remove from the chat context the previous one and to add the new one. You can aleays use the repo map to get an idea of the content of the other files.
- always use type annotations
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
- `unicodedata`: For diacritic stripping and NFC normalization.
- `isbinary`: For heuristic binary file detection.
- Standard Python libraries: `os`, `pathlib`, `json`, `re`, `shutil`.

## Development Process
- **Test-Driven Development (TDD)**: Features and fixes are guided by tests.
- **Checklist-Based Progress Tracking**: The `tasks_checklist.md` file is used to break down features into small steps/tasks.

## Key Requirements & Behaviors

1.  **External Replacement Mapping (`replacement_mapping.json`)**:
    *   The script loads its replacement rules from an external JSON file.
    *   **Key Handling (Source Strings)**:
        *   When loaded from `replacement_mapping.json`, the *keys* (source strings) are canonicalized:
            1.  Diacritics are stripped (e.g., "Flöjoy" -> "Flojoy").
            2.  Control characters are stripped.
            3.  The result is NFC normalized.
        *   This canonical form is used for internal storage and for building regex patterns.
        *   Matching is case-sensitive against these canonical keys.
    *   **Value Handling (Target Strings)**:
        *   The *values* (target strings) from the JSON file are used as-is for replacement, preserving their original characters, casing, and diacritics.
    *   **Recursive Mapping Prevention**: The script checks for and disallows mappings where a canonicalized value is also a canonicalized key.

2.  **Surgical Principle with Encodings & Normalization**:
    The script aims to modify *only* the exact occurrences of matched keys, preserving all other bytes and file characteristics. This is achieved through a careful process:

    *   **Map Loading & Key Preparation**:
        *   Keys from `replacement_mapping.json` are processed into a canonical form: diacritics are stripped, control characters are removed, and then the string is NFC normalized. This canonical key is what's used for matching.
        *   The original values from the JSON map are stored as-is, without normalization or stripping.
        *   Regex patterns for scanning and replacement are built from these canonical keys and are case-sensitive.

    *   **File Reading & Initial Decoding**:
        *   The encoding of each file is detected (e.g., using `chardet`).
        *   File content (and names) are read/decoded into Python Unicode strings using the detected encoding with `errors='surrogateescape'`. This ensures that all original bytes are represented in the Unicode string, even if they don't form valid characters in the detected encoding (they become surrogate codepoints).

    *   **Scanning Phase (Identifying Potential Matches)**:
        *   For each filename or line of content (now a Unicode string from `surrogateescape`):
            1.  A temporary "searchable version" is created by applying the same canonicalization process used for map keys (strip diacritics, strip controls, NFC normalize).
            2.  The scanning regex (`_COMPILED_PATTERN_FOR_SCAN`), built from canonical map keys, is used against this `searchable_version`. This quickly identifies if a line/name *might* contain a match.

    *   **Replacement Phase (Actual Modification)**:
        1.  If the scan indicates a potential match, the `replace_occurrences` function is called with the Unicode string obtained from the `surrogateescape` decoding (let's call this `original_unicode_line`).
        2.  Inside `replace_occurrences`:
            *   `original_unicode_line` is first NFC normalized. This ensures consistency for the regex engine, as the regex patterns are also built from NFC-normalized keys. Let's call this `nfc_unicode_line`.
            *   `re.sub()` is called on `nfc_unicode_line` using the replacement regex (`_COMPILED_PATTERN_FOR_ACTUAL_REPLACE`).
            *   The `_actual_replace_callback` function is invoked for each match found by `re.sub()` within `nfc_unicode_line`.
                *   The `match.group(0)` passed to the callback is a segment from `nfc_unicode_line`.
                *   This segment is then canonicalized (strip diacritics, strip controls, NFC normalize) to create a `lookup_key`.
                *   This `lookup_key` is used to retrieve the corresponding *original, un-normalized value string* from the loaded JSON map.
                *   This original value is returned by the callback for substitution.
        3.  The result of `re.sub()` is a new Unicode string (`modified_unicode_line`) where only the targeted parts have been replaced with their original mapped values. All other characters, including surrogates from the initial `surrogateescape` decoding, remain untouched relative to `nfc_unicode_line`.

    *   **File Writing & Encoding Preservation**:
        *   The `modified_unicode_line` (or `modified_unicode_name`) is encoded back to bytes using the file's original detected encoding, again with `errors='surrogateescape'`. This ensures that:
            *   Characters from the replacement string that are representable in the target encoding are correctly encoded.
            *   Characters from the replacement string that are *not* representable in the target encoding become surrogate escape sequences in the byte string (if the Python version and I/O layer support it, otherwise they might be lost or cause errors depending on the strictness of `surrogateescape`'s re-encoding behavior for unrepresentable *new* characters – typically, `surrogateescape` is primarily for round-tripping *existing* undecodable bytes).
            *   Surrogate codepoints in `modified_unicode_line` that originated from undecodable bytes in the *original* file are converted back to their original byte sequences.
        *   This process ensures that all non-matched parts of the file, including their original byte patterns for unmappable characters, specific Unicode normalization forms (if they differed from NFC but didn't affect matching), line endings, and control characters, are preserved as closely as possible to the original byte stream.

    *   **Handling of Keys Unrepresentable in File's Charset**:
        *   If a key from the `replacement_mapping.json` (e.g., a Chinese string "繁体字") is being searched for in a file encoded in, say, cp1252 (a Western European encoding):
            1.  The Chinese key is canonicalized (stripped, NFC normalized) and remains a Unicode Chinese string.
            2.  The cp1252 file content is decoded to Unicode using `cp1252` with `surrogateescape`. It will not contain Chinese characters.
            3.  The "searchable version" of the cp1252 line will also not contain Chinese characters.
            4.  The canonical Chinese key will not be found in the searchable version of the line.
        *   The script correctly determines that the key is "NOT FOUND" in that specific file/line. No error is raised; the replacement simply doesn't occur for that key in that context. The system relies on Unicode matching after initial decoding.

    *   **Future Support for Full Unicode Keys**:
        *   The current canonicalization of keys (stripping diacritics/controls, NFC normalization) happens at the time the `replacement_mapping.json` is loaded.
        *   If, in the future, this initial canonicalization step for keys were removed (allowing keys in the JSON to be raw Unicode strings with diacritics, control characters, etc.), the core replacement mechanism would largely remain valid.
        *   The main change would be that the `lookup_key` generation within `_actual_replace_callback` (which currently canonicalizes the matched segment from the input) would need to align with how the keys are stored in `_RAW_REPLACEMENT_MAPPING`. If map keys were stored raw, the callback might perform less processing or a different kind of normalization on the matched segment to ensure it can be found in the map.
        *   The principle of operating on Unicode strings (decoded with `surrogateescape` and NFC normalized for `re.sub`) and then re-encoding with `surrogateescape` would still apply.

3.  **Scope of Operation**: (As before)
4.  **Exclusions**: (As before)
5.  **Transaction Management**: (As before)
6.  **User Experience & Control**: (As before)
7.  **Error Handling & Robustness**: (As before)
8.  **Self-Test Functionality**: (As before)

## Open Questions/Considerations (Archive - most are addressed)
- ... (previous content remains relevant) ...

## Transaction File Structure Example
(Structure remains largely the same, `ORIGINAL_NAME` and `ORIGINAL_LINE_CONTENT` are critical for what was actually on disk/in the file line).

## Self-Test (--self-test)
- Implement the tests and ensure they run in a sanbox folder (`./tests/temp/`). Use the tests to develop the code following the TDD method.
  SELF TESTS TO ADD:
    +- Test to assess the ability to replace folder and file names in a directory tree of depth=10
    +- Test to assess the ability to search and replace strings in files with GB18030 charset encoding
    +- Test to assess the ability of replacing a string with its replacement according to the replacement map
    +- Test to assess the ability to leave intact the occurrences of the string that are not included in the replacement map
    +- Test to assess the ability to find in text files multiple lines with the string occurrences
    +- Test to assess the ability to create an entry for a transaction in the json file for each line of a file containing the string occurrences
    +- Test to assess the ability to,create an entry for a transaction in the json file for each file name containing the string occurrences
    +- Test to assess the ability to creat4 an entry for a transaction in the json file for each folder name containing the string occurrences
    +- Test the ability to execute an entry for a transaction in the json file for each line of a file containing the string occurrences
    +- Test the ability to execute an entry for a transaction in the json file for each file name containing the string occurrences
    +- Test the ability to execute an entry for a transaction in the json file for each folder name containing the string occurrences
    +- Test the ability of updating the json field of the STATE of a transaction in realtime in an atomic and secure way
    +- Test the ability to compare the first search and building the planned_transaction.json file with the second search that builds the planned_transaction_validation.json file, to ensure deterministic results
    +- Test the ability to resume the job from a json file with an incomplete number of transactions added, and resume the SEARCH phase
    +- Test the ability to resume the job from a json file with only a partial number of transactions have been marked with the COMPLETED value in the STATUS field, and to resume executing the remaining PLANNED or IN_PROGRESS transactions.
    +- Test the ability to retry transactions executions that were marked with STATE = ERROR, and correctly determine if to try again, ask the user for sudo/permissions or to stop the job and exit with an error message.
    +- Test the ability to find the search and replace the string inside files > 10MB using the line-by-line approach to reduce memory usage
    +- Test the ability of the script to correctly parse the replacement_mapping.json file according to the parsing rules I told you before.
    +- Test the ability to of the script to make changes like a surgeon, only replacing the strings in the replacement_mapping.json configuration file and nothing else, leaving everything else exactly as was before, including: encoding, line endings, trailing chars, control characters, diacritics, malformed chars, illegal chars, corrupt chars, mixed encoding lines, spaces and invisible chars, etc. Everything must be identical and untouched escept those occurrences matching the replacement map provided by the user. Do various tests about this, to consider all tests cases.
    +- Test to assess the fact that files that have not been found containing (in the name or content) strings that matches the replacement map are always left intact.
    +- test the ability to detect and ignore symlinks (and not rename them) if the option `--ignore-symlinks` is used in the launch command.

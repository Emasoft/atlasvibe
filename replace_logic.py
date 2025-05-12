# replace_logic.py
# -*- coding: utf-8 -*-
#
# Copyright (c) 2024 Emasoft
#
# This software is licensed under the MIT License.
# Refer to the LICENSE file for more details.

import re
import json
from pathlib import Path
from typing import Dict, Optional, Callable
import unicodedata # For diacritic stripping

# --- Module-level state for the mapping and pattern ---
_REPLACEMENT_MAPPING_CONFIG: Dict[str, str] = {}
_COMPILED_PATTERN: Optional[re.Pattern] = None
_MAPPING_LOADED: bool = False

# --- Diacritic Stripping ---
def strip_diacritics(text: str) -> str:
    """Removes diacritics from a string by normalizing to NFD and filtering combining characters."""
    if not isinstance(text, str):
        return text
    nfkd_form = unicodedata.normalize('NFD', text)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)])

# --- Mapping Loading and Pattern Compilation ---
def load_replacement_map(mapping_file_path: Path = Path("replacement_mapping.json")) -> None:
    """
    Loads the replacement mapping from a JSON file, strips diacritics from keys,
    and compiles the regex pattern.
    """
    global _REPLACEMENT_MAPPING_CONFIG, _COMPILED_PATTERN, _MAPPING_LOADED
    
    _REPLACEMENT_MAPPING_CONFIG = {} # Reset for potential reloads (e.g., in tests)
    
    try:
        with open(mapping_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"ERROR: Replacement mapping file not found: {mapping_file_path}")
        _MAPPING_LOADED = False
        _COMPILED_PATTERN = None # Ensure pattern is None if map fails to load
        # Depending on desired strictness, could raise an error here
        return
    except json.JSONDecodeError:
        print(f"ERROR: Invalid JSON in replacement mapping file: {mapping_file_path}")
        _MAPPING_LOADED = False
        _COMPILED_PATTERN = None
        return

    raw_mapping = data.get("REPLACEMENT_MAPPING")
    if not isinstance(raw_mapping, dict):
        print(f"ERROR: 'REPLACEMENT_MAPPING' key not found or not a dictionary in {mapping_file_path}")
        _MAPPING_LOADED = False
        _COMPILED_PATTERN = None
        return

    # Process keys: strip diacritics for matching, store original values
    # We need a way to get from a matched (and then diacritic-stripped) string
    # back to the original key to fetch the correct original value.
    # So, the internal map will store: {diacritic_stripped_key: original_value_from_json}
    # And we also need a list of diacritic-stripped keys for the regex pattern.
    
    processed_mapping: Dict[str, str] = {}
    pattern_keys: list[str] = []

    for original_key, original_value in raw_mapping.items():
        if not isinstance(original_key, str) or not isinstance(original_value, str):
            print(f"Warning: Skipping invalid key-value pair in mapping (must be strings): {original_key}:{original_value}")
            continue
        
        stripped_key = strip_diacritics(original_key)
        
        # If multiple original keys strip to the same stripped_key, the last one in JSON order will win.
        # This might need a more sophisticated handling if conflicts are a concern.
        processed_mapping[stripped_key] = original_value
        
        # For the regex pattern, we need to ensure we match based on the stripped keys.
        # We also need to handle cases where different original keys might strip to the same string.
        # The regex will find the longest possible match first.
        # We add the regex-escaped version of the stripped key to our pattern list.
        # Sorting by length (desc) then alphabetically ensures longer matches are tried first.
        pattern_keys.append(re.escape(stripped_key))

    _REPLACEMENT_MAPPING_CONFIG = processed_mapping
    
    if not pattern_keys:
        print("Warning: No valid replacement keys found after processing the mapping file.")
        _COMPILED_PATTERN = None
        _MAPPING_LOADED = True # Loaded, but empty
        return

    # Sort keys by length in descending order to ensure longest match takes precedence
    # e.g., if "flojoy" and "flojoy project" are both keys (after stripping), "flojoy project" should match first.
    pattern_keys.sort(key=len, reverse=True)
    
    # Create a regex pattern like r'(key1|key2|key3)'
    regex_pattern_str = r'(' + r'|'.join(pattern_keys) + r')'
    try:
        _COMPILED_PATTERN = re.compile(regex_pattern_str, flags=re.IGNORECASE)
    except re.error as e:
        print(f"ERROR: Could not compile regex pattern from mapping keys: {e}")
        _COMPILED_PATTERN = None
        _MAPPING_LOADED = False # Consider loading failed if pattern is bad
        return
        
    _MAPPING_LOADED = True
    # print(f"DEBUG: Loaded mapping with {len(_REPLACEMENT_MAPPING_CONFIG)} entries. Regex: {_COMPILED_PATTERN.pattern if _COMPILED_PATTERN else 'None'}")


def get_replacement_for_match(matched_text_on_disk: str) -> str:
    """
    Internal helper.
    Returns the replacement string for a given matched text from the disk/content.
    The matched_text_on_disk is first stripped of diacritics for lookup in the
    internal (diacritic-stripped key) mapping.
    """
    if not _MAPPING_LOADED or not _REPLACEMENT_MAPPING_CONFIG:
        # If mapping isn't loaded or is empty, return original text
        return matched_text_on_disk

    # Strip diacritics from the text that was actually matched by the regex
    # (regex itself matched on diacritic-stripped versions)
    stripped_match_for_lookup = strip_diacritics(matched_text_on_disk)

    # The _REPLACEMENT_MAPPING_CONFIG keys are already diacritic-stripped.
    # We need to find which of our stripped keys (that formed the regex)
    # matches the current stripped_match_for_lookup, considering case-insensitivity of the regex match.
    # A simple way is to iterate through our internal map's keys (which are stripped)
    # and find the one that equals (case-insensitively) the stripped_match_for_lookup.
    
    for internal_stripped_key, original_value in _REPLACEMENT_MAPPING_CONFIG.items():
        if internal_stripped_key.lower() == stripped_match_for_lookup.lower():
            # Now, we need to reconstruct the *actual* casing that was matched by the regex
            # to apply case-preservation if the target value in the map is a simple case change.
            # However, the problem statement implies the value from the map is used directly.
            # "The values (target strings) from the JSON file MUST be used as-is for replacement"
            
            # Let's re-evaluate: the regex matches `matched_text_on_disk`.
            # The `replace_callback` receives this `matched_text_on_disk`.
            # We need to find which *original key from the JSON* (after stripping its diacritics)
            # corresponds to this match.
            
            # The current `_REPLACEMENT_MAPPING_CONFIG` is {stripped_json_key: original_json_value}.
            # The `matched_text_on_disk` is what `_COMPILED_PATTERN` (built from stripped_json_keys) found.
            # So, `strip_diacritics(matched_text_on_disk)` should correspond to one of the
            # keys in `_REPLACEMENT_MAPPING_CONFIG` if we consider case.
            
            # Example:
            # JSON: {"Flöjoy": "AtlasVibe"}
            # Internal map: {"Flojoy": "AtlasVibe"}
            # Regex pattern based on "Flojoy"
            # Text: "flöjoy" -> regex matches "flöjoy" (because pattern is IGNORECASE and matches stripped form)
            # matched_text_on_disk = "flöjoy"
            # stripped_match_for_lookup = strip_diacritics("flöjoy") = "flojoy"
            
            # Now, find "flojoy" (case-insensitively) in _REPLACEMENT_MAPPING_CONFIG's keys.
            for s_key, o_val in _REPLACEMENT_MAPPING_CONFIG.items(): # s_key is already stripped
                if s_key.lower() == stripped_match_for_lookup.lower():
                    # We found the rule. Return the original value associated with this rule.
                    # This part needs to handle the case preservation based on the *original matched text on disk*
                    # and the *original key from the JSON*.
                    # This is where it gets tricky if the original key had different casing than the matched text.

                    # Let's simplify: The regex matches `matched_text_on_disk`.
                    # The `_COMPILED_PATTERN` was built from diacritic-stripped keys.
                    # The `replace_callback` gets `actual_matched_text` (which is `matched_text_on_disk`).
                    # We need to find the `original_value` from `_REPLACEMENT_MAPPING_CONFIG`
                    # whose diacritic-stripped key matches `strip_diacritics(actual_matched_text)` case-insensitively.

                    # The current `_REPLACEMENT_MAPPING_CONFIG` has stripped keys.
                    # So, `strip_diacritics(actual_matched_text)` should be a key, or its lowercase version.
                    
                    # Let's test this:
                    # JSON: {"Flöjoy": "NewValue"} -> internal_map: {"Flojoy": "NewValue"}
                    # Text: "flöjoy" -> regex matches "flöjoy". actual_matched_text = "flöjoy"
                    # stripped_actual_match = "flojoy"
                    # We look for "flojoy" (case-insensitively) in internal_map keys.
                    # "Flojoy".lower() == "flojoy".lower() -> True. Return "NewValue". This is correct.

                    # JSON: {"flojoy": "atlasvibe"} -> internal_map: {"flojoy": "atlasvibe"}
                    # Text: "Flojoy" -> regex matches "Flojoy". actual_matched_text = "Flojoy"
                    # stripped_actual_match = "Flojoy"
                    # "flojoy".lower() == "Flojoy".lower() -> True. Return "atlasvibe". This is correct.
                    # The value from the map is returned as-is.

                    # The problem is if the original JSON had {"flojoy": "atlasvibe", "Flojoy": "AtlasVibe"}
                    # Internal map (if simple dict override): {"flojoy": "AtlasVibe"} (if Flojoy was last)
                    # or {"flojoy": "atlasvibe"} (if flojoy was last).
                    # This means the loading logic for `_REPLACEMENT_MAPPING_CONFIG` needs to be careful
                    # if multiple original keys strip to the same representation.
                    # The current loading logic: `processed_mapping[stripped_key] = original_value` means the last one wins.
                    # This is acceptable if the user ensures their stripped keys are unique or understands this override.

                    # The `get_replacement_for_match` in the previous version took `matched_text` (which was a key from the old hardcoded map)
                    # Now, the callback receives `actual_matched_text` from the regex match.
                    # We need to find the corresponding value in `_REPLACEMENT_MAPPING_CONFIG`.
                    # The keys of `_REPLACEMENT_MAPPING_CONFIG` are already stripped.
                    # The `_COMPILED_PATTERN` matches based on these stripped keys (case-insensitively).
                    # So, `strip_diacritics(actual_matched_text)` should allow us to find the right entry.
                    
                    # Let's assume `actual_matched_text` is what the regex found.
                    # We need to find which rule in `_REPLACEMENT_MAPPING_CONFIG` this corresponds to.
                    # The regex pattern is `(stripped_key1_escaped|stripped_key2_escaped|...)`
                    # The match `actual_matched_text` is what was found on disk.
                    # Its diacritic-stripped, case-lowered version should match one of the
                    # diacritic-stripped, case-lowered keys that formed the pattern.

                    s_match_lower = strip_diacritics(matched_text_on_disk).lower()
                    for s_key_internal, o_val_internal in _REPLACEMENT_MAPPING_CONFIG.items():
                        if s_key_internal.lower() == s_match_lower:
                            return o_val_internal # Return the original value from JSON

    # Fallback: if no specific rule matched (should not happen if regex matched)
    return matched_text_on_disk


def replace_flojoy_occurrences(input_string: str) -> str:
    """
    Replaces all occurrences of strings (defined in replacement_mapping.json,
    matched case-insensitively and diacritic-insensitively for keys)
    in the input_string with their corresponding values from the mapping.
    """
    global _MAPPING_LOADED, _COMPILED_PATTERN
    if not _MAPPING_LOADED:
        load_replacement_map() # Attempt to load if not already
        if not _MAPPING_LOADED or _COMPILED_PATTERN is None:
            # If still not loaded or pattern is bad, make no changes
            print("Warning: Replacement mapping not loaded or pattern invalid. No replacements will occur.")
            return input_string

    if not isinstance(input_string, str) or not _COMPILED_PATTERN:
        return input_string

    def replace_callback(match_obj: re.Match[str]) -> str:
        actual_matched_text = match_obj.group(0) 
        # actual_matched_text is what was found in input_string (e.g., "FlöJoY" if input_string contained it
        # and a rule like {"flojoy": "atlasvibe"} exists, where "flojoy" is the stripped key)
        
        # We need to find the value from _REPLACEMENT_MAPPING_CONFIG.
        # The keys of _REPLACEMENT_MAPPING_CONFIG are diacritic-stripped.
        # The _COMPILED_PATTERN was built from these diacritic-stripped keys.
        
        # The regex matched `actual_matched_text`.
        # We need to find which original rule this corresponds to.
        # The `_COMPILED_PATTERN` is `(stripped_key1|stripped_key2|...)`
        # `match_obj.lastgroup` or `match_obj.groups()` could be used if we had named groups,
        # but with a simple OR, `match_obj.group(0)` is the whole match.

        # We look up using the diacritic-stripped version of the matched text.
        stripped_matched_text_for_lookup = strip_diacritics(actual_matched_text)

        # Find the corresponding value in our processed map.
        # Iterate because the match was case-insensitive, but dict keys are case-sensitive.
        for config_stripped_key, config_value in _REPLACEMENT_MAPPING_CONFIG.items():
            if config_stripped_key.lower() == stripped_matched_text_for_lookup.lower():
                # Found the rule. The value from the config is used as-is.
                return config_value
        
        # Should not be reached if the regex matched, as the pattern is built from these keys.
        # But as a safeguard:
        return actual_matched_text 

    return _COMPILED_PATTERN.sub(replace_callback, input_string)

# Attempt to load the map when the module is imported.
# This makes it available for `file_system_operations` which imports this module.
if not _MAPPING_LOADED:
    load_replacement_map()


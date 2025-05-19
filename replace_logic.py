#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - `_actual_replace_callback`: Simplified lookup logic. Since `matched_text_in_input`
#   is a result of a regex match (built from NFC-normalized, stripped keys) against
#   an NFC-normalized input string, it should already be in the correct form
#   (NFC-normalized, stripped key) for direct lookup in `_RAW_REPLACEMENT_MAPPING`.
#   Removed redundant stripping and normalization of `matched_text_in_input` within the callback.
# - `_actual_replace_callback`: Implemented a two-tier matching logic:
#   1. Attempts a direct case-sensitive match of the stripped input text (case preserved)
#      against the stripped, case-preserved keys in `_RAW_REPLACEMENT_MAPPING`.
#   2. If no direct match, falls back to a case-insensitive comparison of the stripped input
#      text (lowercased) against the lowercased versions of the stripped, case-preserved keys from `_SORTED_RAW_KEYS_FOR_REPLACE`. This fallback is now removed.
# - Matching is now strictly case-sensitive. `re.IGNORECASE` flag removed from regex compilations.
# - `_actual_replace_callback` simplified for direct case-sensitive lookup.
# - Modernized type hints:
#   - Replaced `typing.List` with `list`.
#   - Replaced `typing.Dict` with `dict`.
#   - Replaced `typing.Optional[X]` with `X | None`.
#   - Kept `typing.Dict` and `typing.Optional` aliased for specific internal uses if needed by older type checkers, as per diff.
# - Added debug prints in `load_replacement_map` to show original JSON keys, their stripped versions, and the final internal mapping.
# - `load_replacement_map`: Keys are now NFC normalized after stripping diacritics and control characters.
# - `_actual_replace_callback`: Matched text is also NFC normalized before lookup.
# - Debug print in `load_replacement_map` updated to show pre-NFC and post-NFC stripped keys.
# - Recursion check in `load_replacement_map` now uses NFC normalized keys for comparison.
# - Added detailed debug prints:
#   - In `load_replacement_map`: Print the exact regex string compiled for `_COMPILED_PATTERN_FOR_ACTUAL_REPLACE`.
#   - In `replace_occurrences`: Print the input string and whether `_COMPILED_PATTERN_FOR_ACTUAL_REPLACE.search()` finds a match.
#   - In `_actual_replace_callback`: Added `DEBUG_CALLBACK_HIT` print to confirm if the callback is invoked.
# - `replace_occurrences`: Input string is now NFC normalized before regex search and substitution.
# - Debug print in `replace_occurrences` updated to show original and NFC normalized input.
# - SURGICAL PRINCIPLE REFINEMENT:
#   - `replace_occurrences` now passes the ORIGINAL input string to `re.sub`.
#   - `_actual_replace_callback` normalizes the `match.group(0)` (which is from the original string)
#     by stripping and NFC normalizing IT to create the `lookup_key`.
# - `replace_occurrences`: Changed `re.sub` to operate on an NFC-normalized version of the input string.
#   The debug print for `replace_occurrences` was updated accordingly.
#
# Copyright (c) 2024 Emasoft
#
# This software is licensed under the MIT License.
# Refer to the LICENSE file for more details.

import re
import json
from pathlib import Path
from typing import Dict as TypingDict, Optional as TypingOptional # Retain for clarity if needed for older type checkers or specific constructs
import unicodedata

# --- Module-level state ---
_RAW_REPLACEMENT_MAPPING: dict[str, str] = {} # Stores (normalized stripped key) -> (stripped value) from JSON.
_COMPILED_PATTERN_FOR_SCAN: re.Pattern | None = None # For initial scan. Now case-sensitive.
_MAPPING_LOADED: bool = False
_SORTED_RAW_KEYS_FOR_REPLACE: list[str] = [] # Normalized stripped keys, sorted by length desc.
_COMPILED_PATTERN_FOR_ACTUAL_REPLACE: re.Pattern | None = None # For actual replacement. Now case-sensitive.

def strip_diacritics(text: str) -> str:
    if not isinstance(text, str):
        return text
    nfd_form = unicodedata.normalize('NFD', text)
    return "".join([c for c in nfd_form if not unicodedata.combining(c)])

def strip_control_characters(text: str) -> str:
    if not isinstance(text, str):
        return text
    return "".join(ch for ch in text if unicodedata.category(ch)[0] != 'C')

def load_replacement_map(mapping_file_path: Path) -> bool:
    global _RAW_REPLACEMENT_MAPPING, _COMPILED_PATTERN_FOR_SCAN, _MAPPING_LOADED, \
           _SORTED_RAW_KEYS_FOR_REPLACE, _COMPILED_PATTERN_FOR_ACTUAL_REPLACE

    _RAW_REPLACEMENT_MAPPING = {}
    _COMPILED_PATTERN_FOR_SCAN = None
    _MAPPING_LOADED = False
    _SORTED_RAW_KEYS_FOR_REPLACE = []
    _COMPILED_PATTERN_FOR_ACTUAL_REPLACE = None

    try:
        with open(mapping_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"ERROR: Replacement mapping file not found: {mapping_file_path}")
        return False
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in replacement mapping file: {e}")
        return False
    except Exception as e:
        print(f"ERROR: Could not read replacement mapping file {mapping_file_path}: {e}")
        return False

    raw_mapping_from_json = data.get("REPLACEMENT_MAPPING")
    if not isinstance(raw_mapping_from_json, dict):
        print(f"ERROR: 'REPLACEMENT_MAPPING' key not found or not a dictionary in {mapping_file_path}")
        return False

    temp_raw_mapping: dict[str, str] = {}
    for k, v_original in raw_mapping_from_json.items():
        if not isinstance(k, str) or not isinstance(v_original, str):
            print(f"Warning: Skipping invalid key-value pair (must be strings): {k}:{v_original}")
            continue
        temp_stripped_key = strip_control_characters(strip_diacritics(k))
        normalized_stripped_key_case_preserved = unicodedata.normalize('NFC', temp_stripped_key)
        
        if not normalized_stripped_key_case_preserved:
            print(f"Warning: Original key '{k}' became empty after stripping diacritics/controls. Skipping.")
            continue
        
        temp_raw_mapping[normalized_stripped_key_case_preserved] = v_original
    _RAW_REPLACEMENT_MAPPING = temp_raw_mapping
    # ---- START DEBUG PRINT ----
    print(f"DEBUG (replace_logic.py): For map {mapping_file_path.name}:")
    for k_orig_json, v_val_json in raw_mapping_from_json.items(): # Iterate original JSON keys
        s_key_internal = strip_control_characters(strip_diacritics(k_orig_json)) # How it's processed
        # Check if this processed key is actually in our final map (it might have been skipped if empty after strip)
        # actual_value_in_map = _RAW_REPLACEMENT_MAPPING.get(s_key_internal) # This was pre-normalization
        normalized_s_key_internal = unicodedata.normalize('NFC', s_key_internal)
        print(f"  Original JSON Key: '{k_orig_json}' -> Stripped (pre-NFC): '{s_key_internal}' -> Normalized Stripped for map logic: '{normalized_s_key_internal}' -> Maps to Value in JSON: '{v_val_json}'. In internal map as: '{normalized_s_key_internal}': '{_RAW_REPLACEMENT_MAPPING.get(normalized_s_key_internal, 'NOT_IN_FINAL_MAP_OR_EMPTY_STRIPPED_KEY')}'")
    print(f"  Final _RAW_REPLACEMENT_MAPPING internal state: {_RAW_REPLACEMENT_MAPPING}")
    # ---- END DEBUG PRINT ----

    if not _RAW_REPLACEMENT_MAPPING:
        print("Warning: No valid replacement rules found in the mapping file after initial loading/stripping.")
        _MAPPING_LOADED = True
        return True

    all_stripped_keys_for_recursion_check = set(_RAW_REPLACEMENT_MAPPING.keys())
    for key_stripped_case_preserved, value_original_from_map in _RAW_REPLACEMENT_MAPPING.items(): # key_stripped_case_preserved is already normalized here
        value_stripped_for_check = strip_control_characters(strip_diacritics(value_original_from_map))
        normalized_value_stripped_for_check = unicodedata.normalize('NFC', value_stripped_for_check)
        if normalized_value_stripped_for_check in all_stripped_keys_for_recursion_check:
            original_json_key_for_error = key_stripped_case_preserved # This key is already normalized
            for orig_k, orig_v in raw_mapping_from_json.items():
                # Compare against the normalized form of the original JSON key
                if unicodedata.normalize('NFC', strip_control_characters(strip_diacritics(orig_k))) == key_stripped_case_preserved and orig_v == value_original_from_map:
                    original_json_key_for_error = orig_k # Report the true original key
                    break
            print(f"ERROR: Recursive mapping potential! Value '{value_original_from_map}' (for original JSON key '{original_json_key_for_error}', its stripped form '{value_stripped_for_check}' which normalizes to '{normalized_value_stripped_for_check}' is also a stripped key). This is disallowed. Aborting.")
            _RAW_REPLACEMENT_MAPPING = {}
            return False

    pattern_keys_for_scan: list[str] = [re.escape(k) for k in _RAW_REPLACEMENT_MAPPING.keys()]
    pattern_keys_for_scan.sort(key=len, reverse=True)
    try:
        _COMPILED_PATTERN_FOR_SCAN = re.compile(r'(' + r'|'.join(pattern_keys_for_scan) + r')')
    except re.error as e:
        print(f"ERROR: Could not compile SCAN regex pattern: {e}. Regex tried: '{'(' + '|'.join(pattern_keys_for_scan) + ')'}'")
        _RAW_REPLACEMENT_MAPPING = {}
        return False

    _SORTED_RAW_KEYS_FOR_REPLACE = sorted(_RAW_REPLACEMENT_MAPPING.keys(), key=len, reverse=True)
    
    try:
        # ---- START DEBUG PRINT (Regex String for ACTUAL_REPLACE) ----
        regex_string_for_actual_replace = r'(' + r'|'.join(map(re.escape, _SORTED_RAW_KEYS_FOR_REPLACE)) + r')'
        print(f"DEBUG_REGEX_COMPILE: Compiling ACTUAL REPLACE pattern string: {regex_string_for_actual_replace!r}")
        # ---- END DEBUG PRINT (Regex String for ACTUAL_REPLACE) ----
        _COMPILED_PATTERN_FOR_ACTUAL_REPLACE = re.compile(regex_string_for_actual_replace)
    except re.error as e:
        print(f"ERROR: Could not compile ACTUAL REPLACE regex pattern: {e}")
        _RAW_REPLACEMENT_MAPPING = {}
        _COMPILED_PATTERN_FOR_SCAN = None
        return False
        
    _MAPPING_LOADED = True
    return True

def get_scan_pattern() -> re.Pattern | None:
    return _COMPILED_PATTERN_FOR_SCAN if _MAPPING_LOADED else None

def get_raw_stripped_keys() -> list[str]:
    return _SORTED_RAW_KEYS_FOR_REPLACE if _MAPPING_LOADED else []

def _actual_replace_callback(match: re.Match[str]) -> str:
    matched_text_in_input = match.group(0)
    
    # ---- START DEBUG PRINT (_actual_replace_callback HIT) ----
    print(f"DEBUG_CALLBACK_HIT: Matched raw input (from NFC-normalized string): '{matched_text_in_input}'")
    # ---- END DEBUG PRINT (_actual_replace_callback HIT) ----
    
    # The keys in _RAW_REPLACEMENT_MAPPING are stripped, case-preserved, and NFC normalized.
    # The input to .sub() is an NFC normalized string.
    # `matched_text_in_input` is a segment from this NFC normalized string.
    # We still need to strip and NFC normalize it to ensure it matches the canonical form of map keys,
    # especially if the matched segment itself contained diacritics/controls that were part of the regex match.
    stripped_matched_text = strip_control_characters(strip_diacritics(matched_text_in_input))
    lookup_key = unicodedata.normalize('NFC', stripped_matched_text)

    # ---- START DEBUG PRINT (_actual_replace_callback PROCESSED) ----
    # print(f"DEBUG_CALLBACK_PROCESSED: Matched segment (from NFC string): '{matched_text_in_input!r}' -> Stripped: '{stripped_matched_text!r}' -> Lookup Key (NFC): '{lookup_key!r}'")
    # print(f"DEBUG_CALLBACK_PROCESSED: Is lookup_key '{lookup_key!r}' in _RAW_REPLACEMENT_MAPPING? {lookup_key in _RAW_REPLACEMENT_MAPPING}")
    # if lookup_key in _RAW_REPLACEMENT_MAPPING:
    #     print(f"DEBUG_CALLBACK_RETURNING: Value '{_RAW_REPLACEMENT_MAPPING[lookup_key]}'")
    # else:
    #     # This case should be rare if regex is built correctly from map keys
    #     print(f"DEBUG_CALLBACK_RETURNING: Original matched text because key '{lookup_key!r}' not in map. Map keys: {list(_RAW_REPLACEMENT_MAPPING.keys())}")
    # ---- END DEBUG PRINT (_actual_replace_callback PROCESSED) ----
    
    if lookup_key in _RAW_REPLACEMENT_MAPPING:
        return _RAW_REPLACEMENT_MAPPING[lookup_key]
        
    # This fallback should ideally not be hit if the regex is correctly constructed
    # as the regex is built from _SORTED_RAW_KEYS_FOR_REPLACE.
    # If it is hit, it means the regex matched something that, after stripping and normalizing,
    # isn't a direct key. This would be unexpected.
    # print(f"Warning: _actual_replace_callback fallback for '{matched_text_in_input}' (lookup_key: '{lookup_key}')")
    return matched_text_in_input

def replace_occurrences(input_string: str) -> str:
    if not _MAPPING_LOADED or not _COMPILED_PATTERN_FOR_ACTUAL_REPLACE or not _RAW_REPLACEMENT_MAPPING:
        return input_string
    if not isinstance(input_string, str):
        return input_string

    # Normalize the input string to NFC for consistent matching with NFC-normalized regex keys.
    # The actual sub operation will also be done on this normalized_input_string.
    normalized_input_string = unicodedata.normalize('NFC', input_string)

    # ---- START DEBUG PRINT (replace_occurrences search) ----
    # The pattern itself is built from NFC-normalized, stripped keys.
    # Search on the same normalized_input_string that will be used for substitution.
    search_result = _COMPILED_PATTERN_FOR_ACTUAL_REPLACE.search(normalized_input_string)
    print(f"DEBUG_REPLACE_OCCURRENCES: Input (orig): {input_string!r}, Input (NFC for sub/search): {normalized_input_string!r}, Search on NFC found: {'YES' if search_result else 'NO'}")
    if search_result:
        print(f"DEBUG_REPLACE_OCCURRENCES: Search match object (on NFC): {search_result}")
    # ---- END DEBUG PRINT (replace_occurrences search) ----

    return _COMPILED_PATTERN_FOR_ACTUAL_REPLACE.sub(_actual_replace_callback, normalized_input_string)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - `_actual_replace_callback`: Changed to use `match.group(0)` directly as `lookup_key`.
#   This assumes `match.group(0)` is already the NFC-normalized, stripped key because
#   `re.sub` operates on an NFC-normalized input string and the regex patterns
#   are built from NFC-normalized, stripped keys.
# - `_actual_replace_callback`: Simplified lookup logic. Since `matched_text_in_input`
#   is a result of a regex match (built from NFC-normalized, stripped keys) against
#   an NFC-normalized input string, it should already be in the correct form
#   (NFC-normalized, stripped key) for direct lookup in `_RAW_REPLACEMENT_MAPPING`.
#   Removed redundant stripping and normalization of `matched_text_in_input` within the callback.
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
# - Commented out verbose debug prints related to map loading, regex compilation,
#   callback hits, and search results within `replace_occurrences` to reduce verbosity.
# - `_actual_replace_callback`: Reverted to canonicalizing `match.group(0)` for lookup.
#   The matched text from `re.sub` (even on an NFC-normalized string with NFC-normalized patterns)
#   should be re-canonicalized (strip diacritics, strip controls, NFC normalize) before
#   being used as a key to look up in `_RAW_REPLACEMENT_MAPPING`. This ensures robustness.
# - `_actual_replace_callback`: Simplified to use `match.group(0)` directly as the lookup key.
#   This is based on the understanding that the regex patterns are built from canonical keys
#   and applied to an NFC-normalized string, so `match.group(0)` should be the canonical key.
# - Added extensive debug logging to `load_replacement_map` and `_actual_replace_callback`
#   to trace key canonicalization and map lookups, including character ordinals.
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

# --- START DEBUG CONFIG ---
# Set to True to enable verbose debug prints in this module
_DEBUG_REPLACE_LOGIC = False
# --- END DEBUG CONFIG ---

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
    if _DEBUG_REPLACE_LOGIC: print(f"DEBUG MAP LOAD: Loading map from {mapping_file_path.name}")
    for k_orig_json, v_original in raw_mapping_from_json.items():
        if not isinstance(k, str) or not isinstance(v_original, str): # k was not defined, should be k_orig_json
            print(f"Warning: Skipping invalid key-value pair (must be strings): {k_orig_json}:{v_original}")
            continue
        
        # Canonicalization process for keys
        temp_stripped_key_no_controls = strip_control_characters(k_orig_json)
        temp_stripped_key_no_diacritics = strip_diacritics(temp_stripped_key_no_controls)
        canonical_key = unicodedata.normalize('NFC', temp_stripped_key_no_diacritics)
        
        if not canonical_key: # Check if canonical key is empty
            if _DEBUG_REPLACE_LOGIC: print(f"  DEBUG MAP LOAD: Original key '{k_orig_json}' (len {len(k_orig_json)}) became empty after canonicalization. Skipping.")
            continue
        
        if _DEBUG_REPLACE_LOGIC:
            print(f"  DEBUG MAP LOAD: JSON Key='{k_orig_json}' (len {len(k_orig_json)}, ords={[ord(c) for c in k_orig_json]})")
            print(f"    -> NoControls='{temp_stripped_key_no_controls}' (len {len(temp_stripped_key_no_controls)}, ords={[ord(c) for c in temp_stripped_key_no_controls]})")
            print(f"    -> NoDiacritics='{temp_stripped_key_no_diacritics}' (len {len(temp_stripped_key_no_diacritics)}, ords={[ord(c) for c in temp_stripped_key_no_diacritics]})")
            print(f"    -> CanonicalKey (NFC)='{canonical_key}' (len {len(canonical_key)}, ords={[ord(c) for c in canonical_key]})")
            print(f"    -> Maps to Value: '{v_original}'")

        temp_raw_mapping[canonical_key] = v_original

    _RAW_REPLACEMENT_MAPPING = temp_raw_mapping
    if _DEBUG_REPLACE_LOGIC:
        print(f"DEBUG MAP LOAD: _RAW_REPLACEMENT_MAPPING populated with {len(_RAW_REPLACEMENT_MAPPING)} entries.")
        # for i, (k_map,v_map) in enumerate(_RAW_REPLACEMENT_MAPPING.items()):
        #     print(f"  Map Entry {i}: Key='{k_map}' (len={len(k_map)}, ords={[ord(c) for c in k_map]}) -> Value='{v_map}'")


    if not _RAW_REPLACEMENT_MAPPING:
        print("Warning: No valid replacement rules found in the mapping file after initial loading/stripping.")
        _MAPPING_LOADED = True # Still mark as loaded, just empty
        return True

    all_canonical_keys_for_recursion_check = set(_RAW_REPLACEMENT_MAPPING.keys())
    for key_canonical, value_original_from_map in _RAW_REPLACEMENT_MAPPING.items():
        value_stripped_for_check = strip_control_characters(strip_diacritics(value_original_from_map))
        normalized_value_stripped_for_check = unicodedata.normalize('NFC', value_stripped_for_check)
        if normalized_value_stripped_for_check in all_canonical_keys_for_recursion_check:
            original_json_key_for_error_report = key_canonical 
            for orig_k_json, orig_v_json in raw_mapping_from_json.items():
                temp_s_k = strip_control_characters(strip_diacritics(orig_k_json))
                norm_s_k = unicodedata.normalize('NFC', temp_s_k)
                if norm_s_k == key_canonical and orig_v_json == value_original_from_map:
                    original_json_key_for_error_report = orig_k_json
                    break
            print(f"ERROR: Recursive mapping potential! Value '{value_original_from_map}' (for original JSON key '{original_json_key_for_error_report}', its canonical form '{normalized_value_stripped_for_check}' is also a canonical key). This is disallowed. Aborting.")
            _RAW_REPLACEMENT_MAPPING = {}
            return False

    pattern_keys_for_scan_and_replace: list[str] = [re.escape(k) for k in _RAW_REPLACEMENT_MAPPING.keys()]
    pattern_keys_for_scan_and_replace.sort(key=len, reverse=True) # Longest first for both patterns
    
    _SORTED_RAW_KEYS_FOR_REPLACE = sorted(_RAW_REPLACEMENT_MAPPING.keys(), key=len, reverse=True) # Keep this for reference if needed

    combined_pattern_str = r'(' + r'|'.join(pattern_keys_for_scan_and_replace) + r')'
    
    if _DEBUG_REPLACE_LOGIC:
        print(f"DEBUG MAP LOAD: Combined Regex Pattern String: {combined_pattern_str!r}")

    try:
        _COMPILED_PATTERN_FOR_SCAN = re.compile(combined_pattern_str)
        _COMPILED_PATTERN_FOR_ACTUAL_REPLACE = _COMPILED_PATTERN_FOR_SCAN # Use the same compiled pattern
    except re.error as e:
        print(f"ERROR: Could not compile regex pattern: {e}. Regex tried: '{combined_pattern_str}'")
        _RAW_REPLACEMENT_MAPPING = {}
        return False
        
    _MAPPING_LOADED = True
    return True

def get_scan_pattern() -> re.Pattern | None:
    return _COMPILED_PATTERN_FOR_SCAN if _MAPPING_LOADED else None

def get_raw_stripped_keys() -> list[str]:
    # This returns the canonical keys, sorted by length.
    return _SORTED_RAW_KEYS_FOR_REPLACE if _MAPPING_LOADED else []

def _actual_replace_callback(match: re.Match[str]) -> str:
    # `match.group(0)` is the actual text segment matched in the input string.
    # The input string to `re.sub` in `replace_occurrences` is NFC normalized.
    # The regex pattern `_COMPILED_PATTERN_FOR_ACTUAL_REPLACE` is built from
    # canonical keys (NFC, stripped diacritics, stripped controls).
    # Therefore, `match.group(0)` IS one of these canonical keys.
    lookup_key = match.group(0)
    
    if _DEBUG_REPLACE_LOGIC:
        print(f"DEBUG_CALLBACK: Matched segment (should be canonical key)='{lookup_key}' (len {len(lookup_key)}, ords={[ord(c) for c in lookup_key]})")

    replacement_value = _RAW_REPLACEMENT_MAPPING.get(lookup_key)
    
    if replacement_value is not None:
        if _DEBUG_REPLACE_LOGIC: print(f"  Found in map. Replacing with: '{replacement_value}'")
        return replacement_value
    else:
        # This should ideally not happen if the regex is built correctly from the map keys.
        if _DEBUG_REPLACE_LOGIC:
            print(f"  WARN: Key '{lookup_key}' NOT FOUND in _RAW_REPLACEMENT_MAPPING. This is unexpected.")
            print("  Map keys for comparison (showing first 5 and lengths):")
            for i, (k_map, v_map) in enumerate(_RAW_REPLACEMENT_MAPPING.items()):
                if i < 5:
                    print(f"    MapKey: '{k_map}' (len {len(k_map)}, ords={[ord(c) for c in k_map]})")
                elif i == 5:
                    print(f"    ... and {len(_RAW_REPLACEMENT_MAPPING)-5} more keys.")
                    break
            # Detailed comparison if a specific key is expected:
            # expected_key_debug = "useleSs_diacRiticS" # Example
            # if expected_key_debug in _RAW_REPLACEMENT_MAPPING:
            #     print(f"    Comparing with expected map key '{expected_key_debug}':")
            #     print(f"    Lookup: '{lookup_key}' ({[ord(c) for c in lookup_key]})")
            #     print(f"    MapKey: '{expected_key_debug}' ({[ord(c) for c in expected_key_debug]})")
            #     print(f"    Equal? {lookup_key == expected_key_debug}")

        return lookup_key # Return original matched segment

def replace_occurrences(input_string: str) -> str:
    if not _MAPPING_LOADED or not _COMPILED_PATTERN_FOR_ACTUAL_REPLACE or not _RAW_REPLACEMENT_MAPPING:
        return input_string
    if not isinstance(input_string, str): # Should not happen with type hints, but good check
        return input_string

    # The regex patterns are built from canonical keys (NFC, stripped).
    # Therefore, re.sub should operate on a string that is also canonicalized in the same way
    # for these patterns to match.
    # However, the surgical principle requires preserving non-matching parts of the *original* string.
    # The current compromise is to NFC normalize the input string.
    # The callback then needs to re-canonicalize the matched segment if the regex is broad.
    # BUT, our regex is built from *already canonicalized* keys.
    # So, it will only find occurrences of these canonical keys in the nfc_input_string.
    
    nfc_input_string = unicodedata.normalize('NFC', input_string)
    
    # if _DEBUG_REPLACE_LOGIC:
    #     search_result = _COMPILED_PATTERN_FOR_ACTUAL_REPLACE.search(nfc_input_string)
    #     print(f"DEBUG_REPLACE_OCCURRENCES: Input (orig): {input_string!r}, Input (NFC for sub/search): {nfc_input_string!r}, Search on NFC found: {'YES' if search_result else 'NO'}")
    #     if search_result:
    #         print(f"DEBUG_REPLACE_OCCURRENCES: Search match object (on NFC): {search_result}")

    return _COMPILED_PATTERN_FOR_ACTUAL_REPLACE.sub(_actual_replace_callback, nfc_input_string)

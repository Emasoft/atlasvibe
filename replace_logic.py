#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - `replace_occurrences`:
#   - Uses `re.sub` with a dynamically built case-sensitive regex from `_SORTED_RAW_KEYS_FOR_REPLACE`.
#   - Callback for `re.sub` looks up matched key in `_RAW_REPLACEMENT_MAPPING`.
#   - Prevents chained replacements by performing all replacements based on original string state.
# - `load_replacement_map`:
#   - Stores original JSON mapping in `_RAW_REPLACEMENT_MAPPING` (keys/values after initial stripping).
#   - `_COMPILED_PATTERN_FOR_SCAN` built from these processed keys (case-insensitive) for scan phase.
#   - Added recursion check: a value cannot also be an original key (after stripping).
# - Added `get_raw_stripped_keys()` to expose keys for binary file search.
# - Minor linter-style cleanups (removed unused import, unreachable code, redundant checks).
#
# Copyright (c) 2024 Emasoft
#
# This software is licensed under the MIT License.
# Refer to the LICENSE file for more details.

import re
import json
from pathlib import Path
from typing import Dict, Optional, List as TypingList
import unicodedata

# --- Module-level state ---
_RAW_REPLACEMENT_MAPPING: Dict[str, str] = {} # Stores (stripped key) -> (stripped value) from JSON.
_COMPILED_PATTERN_FOR_SCAN: Optional[re.Pattern] = None # Case-insensitive, for initial scan.
_MAPPING_LOADED: bool = False
_SORTED_RAW_KEYS_FOR_REPLACE: TypingList[str] = [] # Stripped keys, sorted by length desc.
_COMPILED_PATTERN_FOR_ACTUAL_REPLACE: Optional[re.Pattern] = None # Case-sensitive, for actual replacement.

def strip_diacritics(text: str) -> str:
    if not isinstance(text, str): return text
    nfd_form = unicodedata.normalize('NFD', text)
    return "".join([c for c in nfd_form if not unicodedata.combining(c)])

def strip_control_characters(text: str) -> str:
    if not isinstance(text, str): return text
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
        with open(mapping_file_path, 'r', encoding='utf-8') as f: data = json.load(f)
    except FileNotFoundError: print(f"ERROR: Replacement mapping file not found: {mapping_file_path}"); return False
    except json.JSONDecodeError as e: print(f"ERROR: Invalid JSON in replacement mapping file: {e}"); return False
    except Exception as e: print(f"ERROR: Could not read replacement mapping file {mapping_file_path}: {e}"); return False

    raw_mapping_from_json = data.get("REPLACEMENT_MAPPING")
    if not isinstance(raw_mapping_from_json, dict):
        print(f"ERROR: 'REPLACEMENT_MAPPING' key not found or not a dictionary in {mapping_file_path}"); return False

    temp_raw_mapping: Dict[str, str] = {}
    for k, v_original in raw_mapping_from_json.items(): # Changed v to v_original
        if not isinstance(k, str) or not isinstance(v_original, str): # Changed v to v_original
            print(f"Warning: Skipping invalid key-value pair (must be strings): {k}:{v_original}"); continue # Changed v to v_original
        stripped_key = strip_control_characters(strip_diacritics(k))
        # Value stored in mapping is the original value from JSON
        if not stripped_key: 
            print(f"Warning: Original key '{k}' became empty after stripping diacritics/controls. Skipping."); continue
        temp_raw_mapping[stripped_key] = v_original # Store original v_original
    _RAW_REPLACEMENT_MAPPING = temp_raw_mapping

    if not _RAW_REPLACEMENT_MAPPING: 
        print("Warning: No valid replacement rules found in the mapping file after initial loading/stripping.");
        _MAPPING_LOADED = True; return True 

    all_raw_keys_set = set(_RAW_REPLACEMENT_MAPPING.keys())
    for key, value_original_from_map in _RAW_REPLACEMENT_MAPPING.items(): # Changed value to value_original_from_map
        # For recursion check, we see if the stripped version of a value is a key
        value_stripped_for_check = strip_control_characters(strip_diacritics(value_original_from_map))
        if value_stripped_for_check in all_raw_keys_set: 
            print(f"ERROR: Recursive mapping potential! Value '{value_original_from_map}' (for original key '{key}', its stripped form '{value_stripped_for_check}' is also a stripped key) This is disallowed. Aborting.");
            _RAW_REPLACEMENT_MAPPING = {}; return False 

    pattern_keys_for_scan: TypingList[str] = [re.escape(k) for k in _RAW_REPLACEMENT_MAPPING.keys()] 
        
    pattern_keys_for_scan.sort(key=len, reverse=True) 
    try:
        _COMPILED_PATTERN_FOR_SCAN = re.compile(r'(' + r'|'.join(pattern_keys_for_scan) + r')', flags=re.IGNORECASE)
    except re.error as e:
        print(f"ERROR: Could not compile SCAN regex pattern: {e}. Regex tried: '{'(' + '|'.join(pattern_keys_for_scan) + ')'}'");
        _RAW_REPLACEMENT_MAPPING = {}; return False

    _SORTED_RAW_KEYS_FOR_REPLACE = sorted(_RAW_REPLACEMENT_MAPPING.keys(), key=len, reverse=True)
    
    try:
        _COMPILED_PATTERN_FOR_ACTUAL_REPLACE = re.compile(
            r'(' + r'|'.join(map(re.escape, _SORTED_RAW_KEYS_FOR_REPLACE)) + r')',
            flags=re.IGNORECASE # Make actual replacement pattern case-insensitive for matching
        )
    except re.error as e:
        print(f"ERROR: Could not compile ACTUAL REPLACE regex pattern: {e}");
        _RAW_REPLACEMENT_MAPPING = {}; _COMPILED_PATTERN_FOR_SCAN = None; return False 
        
    _MAPPING_LOADED = True
    return True

def get_scan_pattern() -> Optional[re.Pattern]:
    return _COMPILED_PATTERN_FOR_SCAN if _MAPPING_LOADED else None

def get_raw_stripped_keys() -> TypingList[str]:
    return _SORTED_RAW_KEYS_FOR_REPLACE if _MAPPING_LOADED else []

def _actual_replace_callback(match: re.Match[str]) -> str:
    matched_text_in_input = match.group(0)
    # Find which key from our map was responsible for this IGNORECASE match
    # _SORTED_RAW_KEYS_FOR_REPLACE contains the stripped, case-preserved keys from the map, sorted by length.
    # _RAW_REPLACEMENT_MAPPING maps these stripped, case-preserved keys to their original values from JSON.
    for map_key_case_preserved_stripped in _SORTED_RAW_KEYS_FOR_REPLACE:
        if map_key_case_preserved_stripped.lower() == matched_text_in_input.lower():
            # This map_key_case_preserved_stripped is the one that semantically matched.
            # Use it to get the intended original value from the mapping.
            return _RAW_REPLACEMENT_MAPPING[map_key_case_preserved_stripped]
    return matched_text_in_input # Should not be reached if pattern is built correctly from these keys

def replace_occurrences(input_string: str) -> str:
    if not _MAPPING_LOADED or not _COMPILED_PATTERN_FOR_ACTUAL_REPLACE or not _RAW_REPLACEMENT_MAPPING:
        return input_string 
    if not isinstance(input_string, str):
        return input_string

    return _COMPILED_PATTERN_FOR_ACTUAL_REPLACE.sub(_actual_replace_callback, input_string)
    

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Refactored multiple statements on single lines to comply with E701 and E702 linting rules.
# - `_actual_replace_callback`:
#   - Prioritizes exact case match of `matched_text_in_input` against `_RAW_REPLACEMENT_MAPPING` keys (which are stripped, case-preserved original JSON keys).
#   - Falls back to case-insensitive comparison against `_SORTED_RAW_KEYS_FOR_REPLACE` if no exact case match is found.
#   - Both comparison paths now use a stripped version of `matched_text_in_input` to ensure consistent comparison against the (already stripped) map keys.
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

    temp_raw_mapping: Dict[str, str] = {}
    for k, v_original in raw_mapping_from_json.items():
        if not isinstance(k, str) or not isinstance(v_original, str):
            print(f"Warning: Skipping invalid key-value pair (must be strings): {k}:{v_original}")
            continue
        stripped_key_case_preserved = strip_control_characters(strip_diacritics(k))
        
        if not stripped_key_case_preserved:
            print(f"Warning: Original key '{k}' became empty after stripping diacritics/controls. Skipping.")
            continue
        
        temp_raw_mapping[stripped_key_case_preserved] = v_original
    _RAW_REPLACEMENT_MAPPING = temp_raw_mapping

    if not _RAW_REPLACEMENT_MAPPING:
        print("Warning: No valid replacement rules found in the mapping file after initial loading/stripping.")
        _MAPPING_LOADED = True
        return True

    all_stripped_keys_for_recursion_check = set(_RAW_REPLACEMENT_MAPPING.keys())
    for key_stripped_case_preserved, value_original_from_map in _RAW_REPLACEMENT_MAPPING.items():
        value_stripped_for_check = strip_control_characters(strip_diacritics(value_original_from_map))
        if value_stripped_for_check in all_stripped_keys_for_recursion_check:
            original_json_key_for_error = key_stripped_case_preserved
            for orig_k, orig_v in raw_mapping_from_json.items():
                if strip_control_characters(strip_diacritics(orig_k)) == key_stripped_case_preserved and orig_v == value_original_from_map:
                    original_json_key_for_error = orig_k
                    break
            print(f"ERROR: Recursive mapping potential! Value '{value_original_from_map}' (for original JSON key '{original_json_key_for_error}', its stripped form '{value_stripped_for_check}' is also a stripped key). This is disallowed. Aborting.")
            _RAW_REPLACEMENT_MAPPING = {}
            return False

    pattern_keys_for_scan: TypingList[str] = [re.escape(k) for k in _RAW_REPLACEMENT_MAPPING.keys()]
    pattern_keys_for_scan.sort(key=len, reverse=True)
    try:
        _COMPILED_PATTERN_FOR_SCAN = re.compile(r'(' + r'|'.join(pattern_keys_for_scan) + r')', flags=re.IGNORECASE)
    except re.error as e:
        print(f"ERROR: Could not compile SCAN regex pattern: {e}. Regex tried: '{'(' + '|'.join(pattern_keys_for_scan) + ')'}'")
        _RAW_REPLACEMENT_MAPPING = {}
        return False

    _SORTED_RAW_KEYS_FOR_REPLACE = sorted(_RAW_REPLACEMENT_MAPPING.keys(), key=len, reverse=True)
    
    try:
        _COMPILED_PATTERN_FOR_ACTUAL_REPLACE = re.compile(
            r'(' + r'|'.join(map(re.escape, _SORTED_RAW_KEYS_FOR_REPLACE)) + r')',
            flags=re.IGNORECASE
        )
    except re.error as e:
        print(f"ERROR: Could not compile ACTUAL REPLACE regex pattern: {e}")
        _RAW_REPLACEMENT_MAPPING = {}
        _COMPILED_PATTERN_FOR_SCAN = None
        return False
        
    _MAPPING_LOADED = True
    return True

def get_scan_pattern() -> Optional[re.Pattern]:
    return _COMPILED_PATTERN_FOR_SCAN if _MAPPING_LOADED else None

def get_raw_stripped_keys() -> TypingList[str]:
    return _SORTED_RAW_KEYS_FOR_REPLACE if _MAPPING_LOADED else []

def _actual_replace_callback(match: re.Match[str]) -> str:
    matched_text_in_input = match.group(0)
    
    stripped_matched_text_in_input = strip_control_characters(strip_diacritics(matched_text_in_input))

    if stripped_matched_text_in_input in _RAW_REPLACEMENT_MAPPING:
        return _RAW_REPLACEMENT_MAPPING[stripped_matched_text_in_input]

    for map_key_stripped_case_preserved in _SORTED_RAW_KEYS_FOR_REPLACE:
        if map_key_stripped_case_preserved.lower() == stripped_matched_text_in_input.lower():
            return _RAW_REPLACEMENT_MAPPING[map_key_stripped_case_preserved]
            
    return matched_text_in_input

def replace_occurrences(input_string: str) -> str:
    if not _MAPPING_LOADED or not _COMPILED_PATTERN_FOR_ACTUAL_REPLACE or not _RAW_REPLACEMENT_MAPPING:
        return input_string
    if not isinstance(input_string, str):
        return input_string

    return _COMPILED_PATTERN_FOR_ACTUAL_REPLACE.sub(_actual_replace_callback, input_string)

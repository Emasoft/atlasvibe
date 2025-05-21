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
# - Fixed Ruff linting errors: E701 (multiple statements on one line) and F821 (undefined name `k`).
# - Modified `load_replacement_map` to accept an optional logger. Error/warning messages now use this logger if provided, otherwise fallback to print.
# - Set `_DEBUG_REPLACE_LOGIC` to `False` by default.
# - `_actual_replace_callback`: Re-canonicalize `match.group(0)` before map lookup to ensure robustness.
# - `_actual_replace_callback`: Added a non-debug, warning-level log if a lookup_key is not found in _RAW_REPLACEMENT_MAPPING.
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
import logging

# --- Module-level state ---
_RAW_REPLACEMENT_MAPPING: dict[str, str] = {} # Stores (normalized stripped key) -> (stripped value) from JSON.
_COMPILED_PATTERN_FOR_SCAN: re.Pattern | None = None # For initial scan. Now case-sensitive.
_MAPPING_LOADED: bool = False
_SORTED_RAW_KEYS_FOR_REPLACE: list[str] = [] # Normalized stripped keys, sorted by length desc.
_COMPILED_PATTERN_FOR_ACTUAL_REPLACE: re.Pattern | None = None # For actual replacement. Now case-sensitive.
_MODULE_LOGGER: logging.Logger | None = None # Module-level logger instance

# --- START DEBUG CONFIG ---
# Set to True to enable verbose debug prints in this module
_DEBUG_REPLACE_LOGIC = False
# --- END DEBUG CONFIG ---

def _log_message(level: int, message: str, logger: logging.Logger | None = None):
    """Helper to log messages using provided logger or print as fallback."""
    effective_logger = logger if logger else _MODULE_LOGGER
    if effective_logger:
        effective_logger.log(level, message)
    else:
        # Fallback to print if no logger is available (e.g., during direct script use or testing without logger setup)
        prefix = ""
        if level == logging.ERROR:
            prefix = "ERROR: "
        elif level == logging.WARNING:
            prefix = "WARNING: "
        elif level == logging.INFO:
            prefix = "INFO: "
        print(f"{prefix}{message}")


def strip_diacritics(text: str) -> str:
    if not isinstance(text, str):
        return text
    nfd_form = unicodedata.normalize('NFD', text)
    return "".join([c for c in nfd_form if not unicodedata.combining(c)])

def strip_control_characters(text: str) -> str:
    if not isinstance(text, str):
        return text
    return "".join(ch for ch in text if unicodedata.category(ch)[0] != 'C')

def load_replacement_map(mapping_file_path: Path, logger: logging.Logger | None = None) -> bool:
    global _RAW_REPLACEMENT_MAPPING, _COMPILED_PATTERN_FOR_SCAN, _MAPPING_LOADED, \
           _SORTED_RAW_KEYS_FOR_REPLACE, _COMPILED_PATTERN_FOR_ACTUAL_REPLACE, _MODULE_LOGGER

    _MODULE_LOGGER = logger # Store logger for use by other functions in this module if needed

    _RAW_REPLACEMENT_MAPPING = {}
    _COMPILED_PATTERN_FOR_SCAN = None
    _MAPPING_LOADED = False
    _SORTED_RAW_KEYS_FOR_REPLACE = []
    _COMPILED_PATTERN_FOR_ACTUAL_REPLACE = None

    try:
        with open(mapping_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        _log_message(logging.ERROR, f"Replacement mapping file not found: {mapping_file_path}", logger)
        return False
    except json.JSONDecodeError as e:
        _log_message(logging.ERROR, f"Invalid JSON in replacement mapping file: {e}", logger)
        return False
    except Exception as e:
        _log_message(logging.ERROR, f"Could not read replacement mapping file {mapping_file_path}: {e}", logger)
        return False

    raw_mapping_from_json = data.get("REPLACEMENT_MAPPING")
    if not isinstance(raw_mapping_from_json, dict):
        _log_message(logging.ERROR, f"'REPLACEMENT_MAPPING' key not found or not a dictionary in {mapping_file_path}", logger)
        return False

    temp_raw_mapping: dict[str, str] = {}
    if _DEBUG_REPLACE_LOGIC:
        _log_message(logging.DEBUG, f"DEBUG MAP LOAD: Loading map from {mapping_file_path.name}", logger)

    for k_orig_json, v_original in raw_mapping_from_json.items():
        if not isinstance(k_orig_json, str) or not isinstance(v_original, str):
            _log_message(logging.WARNING, f"Skipping invalid key-value pair (must be strings): {k_orig_json}:{v_original}", logger)
            continue
        
        temp_stripped_key_no_controls = strip_control_characters(k_orig_json)
        temp_stripped_key_no_diacritics = strip_diacritics(temp_stripped_key_no_controls)
        canonical_key = unicodedata.normalize('NFC', temp_stripped_key_no_diacritics)
        
        if not canonical_key:
            if _DEBUG_REPLACE_LOGIC:
                _log_message(logging.DEBUG, f"  DEBUG MAP LOAD: Original key '{k_orig_json}' (len {len(k_orig_json)}) became empty after canonicalization. Skipping.", logger)
            continue
        
        if _DEBUG_REPLACE_LOGIC:
            _log_message(logging.DEBUG, f"  DEBUG MAP LOAD: JSON Key='{k_orig_json}' (len {len(k_orig_json)}, ords={[ord(c) for c in k_orig_json]})", logger)
            _log_message(logging.DEBUG, f"    -> NoControls='{temp_stripped_key_no_controls}' (len {len(temp_stripped_key_no_controls)}, ords={[ord(c) for c in temp_stripped_key_no_controls]})", logger)
            _log_message(logging.DEBUG, f"    -> NoDiacritics='{temp_stripped_key_no_diacritics}' (len {len(temp_stripped_key_no_diacritics)}, ords={[ord(c) for c in temp_stripped_key_no_diacritics]})", logger)
            _log_message(logging.DEBUG, f"    -> CanonicalKey (NFC)='{canonical_key}' (len {len(canonical_key)}, ords={[ord(c) for c in canonical_key]})", logger)
            _log_message(logging.DEBUG, f"    -> Maps to Value: '{v_original}'", logger)

        temp_raw_mapping[canonical_key] = v_original

    _RAW_REPLACEMENT_MAPPING = temp_raw_mapping
    if _DEBUG_REPLACE_LOGIC:
        _log_message(logging.DEBUG, f"DEBUG MAP LOAD: _RAW_REPLACEMENT_MAPPING populated with {len(_RAW_REPLACEMENT_MAPPING)} entries.", logger)

    if not _RAW_REPLACEMENT_MAPPING:
        _log_message(logging.WARNING, "No valid replacement rules found in the mapping file after initial loading/stripping.", logger)
        _MAPPING_LOADED = True
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
            _log_message(logging.ERROR, f"Recursive mapping potential! Value '{value_original_from_map}' (for original JSON key '{original_json_key_for_error_report}', its canonical form '{normalized_value_stripped_for_check}' is also a canonical key). This is disallowed. Aborting.", logger)
            _RAW_REPLACEMENT_MAPPING = {}
            return False

    pattern_keys_for_scan_and_replace: list[str] = [re.escape(k) for k in _RAW_REPLACEMENT_MAPPING.keys()]
    pattern_keys_for_scan_and_replace.sort(key=len, reverse=True)
    
    _SORTED_RAW_KEYS_FOR_REPLACE = sorted(_RAW_REPLACEMENT_MAPPING.keys(), key=len, reverse=True)

    combined_pattern_str = r'(' + r'|'.join(pattern_keys_for_scan_and_replace) + r')'
    
    if _DEBUG_REPLACE_LOGIC:
        _log_message(logging.DEBUG, f"DEBUG MAP LOAD: Combined Regex Pattern String: {combined_pattern_str!r}", logger)

    try:
        _COMPILED_PATTERN_FOR_SCAN = re.compile(combined_pattern_str)
        _COMPILED_PATTERN_FOR_ACTUAL_REPLACE = _COMPILED_PATTERN_FOR_SCAN
    except re.error as e:
        _log_message(logging.ERROR, f"Could not compile regex pattern: {e}. Regex tried: '{combined_pattern_str}'", logger)
        _RAW_REPLACEMENT_MAPPING = {}
        return False
        
    _MAPPING_LOADED = True
    return True

def get_scan_pattern() -> re.Pattern | None:
    return _COMPILED_PATTERN_FOR_SCAN if _MAPPING_LOADED else None

def get_raw_stripped_keys() -> list[str]:
    return _SORTED_RAW_KEYS_FOR_REPLACE if _MAPPING_LOADED else []

def _actual_replace_callback(match: re.Match[str]) -> str:
    matched_text_from_input = match.group(0)
    
    # Canonicalize the matched segment from the input string before lookup
    temp_stripped_no_controls = strip_control_characters(matched_text_from_input)
    temp_stripped_no_diacritics = strip_diacritics(temp_stripped_no_controls)
    lookup_key = unicodedata.normalize('NFC', temp_stripped_no_diacritics)
    
    if _DEBUG_REPLACE_LOGIC:
        _log_message(logging.DEBUG, f"DEBUG_CALLBACK: Matched segment (original from input)='{matched_text_from_input}'", _MODULE_LOGGER)
        _log_message(logging.DEBUG, f"  Canonicalized lookup_key='{lookup_key}' (len {len(lookup_key)}, ords={[ord(c) for c in lookup_key]})", _MODULE_LOGGER)

    replacement_value = _RAW_REPLACEMENT_MAPPING.get(lookup_key)
    
    if replacement_value is not None:
        if _DEBUG_REPLACE_LOGIC:
            _log_message(logging.DEBUG, f"  Found in map. Replacing with: '{replacement_value}'", _MODULE_LOGGER)
        return replacement_value
    else:
        # This log will now appear even if _DEBUG_REPLACE_LOGIC is False, to help diagnose persistent issues.
        _log_message(logging.WARNING, f"REPLACE_LOGIC_WARN: Callback lookup_key '{lookup_key}' (from matched: '{matched_text_from_input}') NOT FOUND in _RAW_REPLACEMENT_MAPPING. Map size: {len(_RAW_REPLACEMENT_MAPPING)}. Returning original matched text.", _MODULE_LOGGER)
        if _DEBUG_REPLACE_LOGIC: # More detailed dump if debug is on
            _log_message(logging.DEBUG, f"  _RAW_REPLACEMENT_MAPPING keys: {list(_RAW_REPLACEMENT_MAPPING.keys())[:20]}...", _MODULE_LOGGER) # Print some keys
        return matched_text_from_input

def replace_occurrences(input_string: str) -> str:
    if not _MAPPING_LOADED or not _COMPILED_PATTERN_FOR_ACTUAL_REPLACE or not _RAW_REPLACEMENT_MAPPING:
        return input_string
    if not isinstance(input_string, str):
        return input_string
    
    nfc_input_string = unicodedata.normalize('NFC', input_string)
    
    # if _DEBUG_REPLACE_LOGIC:
    #     search_result = _COMPILED_PATTERN_FOR_ACTUAL_REPLACE.search(nfc_input_string)
    #     _log_message(logging.DEBUG, f"DEBUG_REPLACE_OCCURRENCES: Input (orig): {input_string!r}, Input (NFC for sub/search): {nfc_input_string!r}, Search on NFC found: {'YES' if search_result else 'NO'}", _MODULE_LOGGER)
    #     if search_result:
    #         _log_message(logging.DEBUG, f"DEBUG_REPLACE_OCCURRENCES: Search match object (on NFC): {search_result}", _MODULE_LOGGER)

    return _COMPILED_PATTERN_FOR_ACTUAL_REPLACE.sub(_actual_replace_callback, nfc_input_string)

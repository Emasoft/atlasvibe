#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Ensured regex pattern compilation uses re.IGNORECASE for case-insensitive matching.
# - Improved fallback logic in replace_occurrences to handle case-insensitive matches robustly.
# - Added detailed docstrings and preserved existing comments.
#
# Copyright (c) 2024 Emasoft
#
# This software is licensed under the MIT License.
# Refer to the LICENSE file for more details.

import re
import json
from pathlib import Path
from typing import Dict, Optional, Callable
import unicodedata  # For diacritic stripping

# --- Module-level state for the mapping and pattern ---
_REPLACEMENT_MAPPING_CONFIG: Dict[str, str] = {}
_COMPILED_PATTERN: Optional[re.Pattern] = None
_MAPPING_LOADED: bool = False

# --- Diacritic and Control Character Stripping ---


def strip_diacritics(text: str) -> str:
    """Removes diacritics from a string by normalizing to NFD and filtering combining characters."""
    if not isinstance(text, str):
        return text
    nfd_form = unicodedata.normalize('NFD', text)
    return "".join([c for c in nfd_form if not unicodedata.combining(c)])


def strip_control_characters(text: str) -> str:
    """Removes C0 and C1 control characters from a string. Spaces are preserved."""
    if not isinstance(text, str):
        return text
    return "".join(ch for ch in text if unicodedata.category(ch)[0] != 'C')


# --- Mapping Loading and Pattern Compilation ---
def load_replacement_map(mapping_file_path: Path) -> bool:
    """
    Loads the replacement mapping from a JSON file.
    Processes keys by:
    1. Stripping diacritics.
    2. Stripping control characters.
    3. Escaping regex metacharacters from the result for pattern compilation.
    The values (target strings) are stored as-is.
    """
    global _REPLACEMENT_MAPPING_CONFIG, _COMPILED_PATTERN, _MAPPING_LOADED

    _REPLACEMENT_MAPPING_CONFIG = {}  # Reset for potential reloads
    _COMPILED_PATTERN = None
    _MAPPING_LOADED = False

    try:
        with open(mapping_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"ERROR: Replacement mapping file not found: {mapping_file_path}")
        return False
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in replacement mapping file: {mapping_file_path}. Details: {e}")
        return False
    except Exception as e:
        print(f"ERROR: Could not read replacement mapping file {mapping_file_path}: {e}")
        return False

    raw_mapping = data.get("REPLACEMENT_MAPPING")
    if not isinstance(raw_mapping, dict):
        print(f"ERROR: 'REPLACEMENT_MAPPING' key not found or not a dictionary in {mapping_file_path}")
        return False

    processed_mapping: Dict[str, str] = {}
    pattern_keys: list[str] = []

    for original_key, original_value in raw_mapping.items():
        if not isinstance(original_key, str) or not isinstance(original_value, str):
            print(f"Warning: Skipping invalid key-value pair in mapping (must be strings): {original_key}:{original_value}")
            continue

        # Process key: 1. Strip diacritics, 2. Strip control characters
        key_after_diacritics = strip_diacritics(original_key)
        processed_key_for_map_and_regex = strip_control_characters(key_after_diacritics)

        # Store the mapping from the fully processed key to the original value from JSON.
        # If multiple original keys process to the same key, the last one encountered will overwrite.
        processed_mapping[processed_key_for_map_and_regex] = original_value

        # For the regex pattern, re.escape() the fully processed key.
        # Avoid adding empty strings to pattern keys if processing results in an empty key
        if processed_key_for_map_and_regex:
            pattern_keys.append(re.escape(processed_key_for_map_and_regex))

    _REPLACEMENT_MAPPING_CONFIG = processed_mapping

    if not pattern_keys:
        print("Warning: No valid, non-empty replacement keys found after processing the mapping file. No pattern compiled.")
        _MAPPING_LOADED = True  # Loaded, but effectively empty
        _COMPILED_PATTERN = None  # Ensure pattern is None
        return True

    # Sort keys by length in descending order to ensure longest match takes precedence.
    pattern_keys.sort(key=len, reverse=True)

    regex_pattern_str = r'(' + r'|'.join(pattern_keys) + r')'
    try:
        _COMPILED_PATTERN = re.compile(regex_pattern_str, flags=re.IGNORECASE)
    except re.error as e:
        print(f"ERROR: Could not compile regex pattern from mapping keys: {e}. Regex tried: '{regex_pattern_str}'")
        _COMPILED_PATTERN = None
        return False  # Failed to compile pattern

    _MAPPING_LOADED = True
    return True


def replace_occurrences(input_string: str) -> str:
    """
    Replaces all occurrences of strings (defined in the loaded mapping file,
    matched based on processed keys: case-insensitively, diacritic-stripped, control-char-stripped)
    in the input_string with their corresponding original values from the mapping.
    Values are used as-is.
    """
    if not _MAPPING_LOADED or _COMPILED_PATTERN is None:
        return input_string

    if not isinstance(input_string, str):
        return input_string

    def replace_callback(match_obj: re.Match[str]) -> str:
        actual_matched_text_on_disk = match_obj.group(0)

        key_after_diacritics = strip_diacritics(actual_matched_text_on_disk)
        processed_match_for_lookup = strip_control_characters(key_after_diacritics)  # This preserves case from disk

        # Prioritize direct (case-sensitive after stripping) match with map keys.
        # The keys in _REPLACEMENT_MAPPING_CONFIG are already stripped of diacritics and control chars,
        # but retain their original casing from the JSON.
        if processed_match_for_lookup in _REPLACEMENT_MAPPING_CONFIG:
            return _REPLACEMENT_MAPPING_CONFIG[processed_match_for_lookup]

        # Fallback for case-insensitive matching if direct case match wasn't found.
        # This is necessary because the main regex is re.IGNORECASE.
        # An input of "floJOY" (matched by regex) might not be a direct key in _REPLACEMENT_MAPPING_CONFIG
        # if the original JSON keys were "flojoy", "Flojoy", etc., and "floJOY" itself wasn't a key.
        # This loop ensures that if the IGNORECASE regex matched, we find *a* corresponding rule.
        processed_match_for_lookup_lower = processed_match_for_lookup.lower()
        for config_key_processed, config_value_original in _REPLACEMENT_MAPPING_CONFIG.items():
            if config_key_processed.lower() == processed_match_for_lookup_lower:
                return config_value_original

        # Should not be reached if the regex matched something that was derived from a config key
        # and the map loading/callback logic is perfectly aligned.
        return actual_matched_text_on_disk

    return _COMPILED_PATTERN.sub(replace_callback, input_string)

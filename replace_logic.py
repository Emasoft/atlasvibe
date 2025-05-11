# replace_logic.py
# -*- coding: utf-8 -*-
#
# Copyright (c) 2024 Emasoft
#
# This software is licensed under the MIT License.
# Refer to the LICENSE file for more details.

import re
from typing import Dict

REPLACEMENT_MAPPING: Dict[str, str] = {
    'flojoy': 'atlasvibe',
    'Flojoy': 'Atlasvibe',
    'floJoy': 'atlasVibe',
    'FloJoy': 'AtlasVibe',
    'FLOJOY': 'ATLASVIBE',
}

def get_replacement_for_match(matched_text: str) -> str:
    """
    Returns the replacement string for a given matched text based on REPLACEMENT_MAPPING.
    If the exact matched text is not a key in REPLACEMENT_MAPPING, it returns the original matched text.
    This ensures that only defined variations of "flojoy" are replaced.
    """
    return REPLACEMENT_MAPPING.get(matched_text, matched_text)

def replace_flojoy_occurrences(input_string: str) -> str:
    """
    Replaces all occurrences of 'flojoy' (case-insensitive) in the input_string
    with its case-preserved 'atlasvibe' equivalent based on REPLACEMENT_MAPPING.
    """
    if not isinstance(input_string, str):
        # Or raise TypeError, depending on desired strictness
        return input_string 

    def replace_callback(match_obj: re.Match[str]) -> str:
        actual_matched_text = match_obj.group(0)
        # The diagnostic prints previously here have been removed as per user request for clean code.
        # The logic relies on REPLACEMENT_MAPPING containing all relevant casings.
        return get_replacement_for_match(actual_matched_text)

    # Use a regex that finds all variations of "flojoy" case-insensitively.
    # The callback then ensures the correct replacement from the mapping.
    # This pattern ensures we only target the specific word "flojoy" and its casings.
    # Using word boundaries (\b) might be too restrictive if "myflojoy_project" should become "myatlasvibe_project".
    # The current REPLACEMENT_MAPPING implies whole-word matches.
    # If "flojoy" can be part of a larger word and still needs replacement based on these rules,
    # the regex might need adjustment, or the mapping expanded.
    # For now, sticking to direct replacement of the keys in the map.
    
    # Construct a regex pattern from the keys of REPLACEMENT_MAPPING to ensure only these are matched.
    # This makes the re.sub more targeted to the specific strings we want to replace.
    # Sort keys by length descending to match longer strings first (e.g., "FloJoy" before "Flojoy" if that were an issue, though re.IGNORECASE handles it well).
    # However, re.IGNORECASE on "flojoy" is simpler and the callback handles the specific casing.
    
    pattern = r'flojoy' # Simple case-insensitive match for "flojoy"
    return re.sub(pattern, replace_callback, input_string, flags=re.IGNORECASE)


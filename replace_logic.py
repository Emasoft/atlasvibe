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
    'Flojoy': 'AtlasVibe', # Corrected casing
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
    replacement = REPLACEMENT_MAPPING.get(matched_text, matched_text)
    # Keep the trace log for debugging if needed during testing
    # print(f"TRACE_REPLACE_LOGIC: Matched {repr(matched_text)}, Returning: {repr(replacement)}")
    return replacement

def replace_flojoy_occurrences(input_string: str) -> str:
    """
    Replaces all occurrences of 'flojoy' (case-insensitive) in the input_string
    with its case-preserved 'atlasvibe' equivalent based on REPLACEMENT_MAPPING.
    """
    if not isinstance(input_string, str):
        # Handle potential non-string inputs gracefully if necessary, though unlikely for file/folder names/lines
        return input_string

    # Define the callback function directly using the helper
    def replace_callback(match_obj: re.Match[str]) -> str:
        actual_matched_text = match_obj.group(0)
        # Use the existing helper function for the lookup logic
        return get_replacement_for_match(actual_matched_text)

    pattern = r'flojoy'
    # Use the simplified callback
    return re.sub(pattern, replace_callback, input_string, flags=re.IGNORECASE)


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
        return input_string 

    def _get_internal_case_preserved_replacement(text_to_match: str) -> str:
        print(f"TRACE_REPLACE_LOGIC: _get_internal_case_preserved_replacement ENTERED with text_to_match: {repr(text_to_match)}")
        result_to_return = None

        if text_to_match in REPLACEMENT_MAPPING:
            result_to_return = REPLACEMENT_MAPPING[text_to_match]
            print(f"TRACE_REPLACE_LOGIC: Matched key {repr(text_to_match)} in REPLACEMENT_MAPPING. Returning: {repr(result_to_return)}")
        else:
            result_to_return = text_to_match 
            print(f"TRACE_REPLACE_LOGIC: No exact match for {repr(text_to_match)} in REPLACEMENT_MAPPING. Fallback returning original: {repr(result_to_return)}")
        
        return result_to_return

    def replace_callback(match_obj: re.Match[str]) -> str:
        actual_matched_text = match_obj.group(0)
        return _get_internal_case_preserved_replacement(actual_matched_text)
    
    pattern = r'flojoy' 
    return re.sub(pattern, replace_callback, input_string, flags=re.IGNORECASE)


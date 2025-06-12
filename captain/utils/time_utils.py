#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Created time_utils module to centralize time-related utilities
# - Moved utcnow_str() function here to avoid duplication
# 

"""Time-related utility functions."""

from datetime import datetime, timezone


def utcnow_str() -> str:
    """Get current UTC time as ISO string.
    
    Returns:
        str: Current UTC time in ISO format.
    """
    return datetime.now(timezone.utc).isoformat()
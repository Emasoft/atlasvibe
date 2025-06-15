#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Example test file for AtlasVibe test sequencer
# Note: Cloud functionality has been removed from AtlasVibe
# These tests demonstrate basic pytest functionality without cloud exports

import pandas as pd


def test_min_max():
    value = 6.15
    # Basic range check
    assert 5.0 <= value <= 10.0


def test_min():
    value = 6.15
    # Check against minimum value
    assert value >= 5.0


def test_max():
    value = 6.15
    # Check against maximum value
    assert value <= 10.0
    # Multiple assertions
    assert 0 < value


def test_dataframe():
    df = pd.DataFrame({"value": [6.15, 6.15, 6.15]})
    # Check DataFrame is valid
    assert df is not None
    assert len(df) == 3
    assert df['value'].mean() == 6.15


def test_failing_example():
    value = 6.15
    # This test will fail as an example
    assert 12 < value  # <-- FAIL
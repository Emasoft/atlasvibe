#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Test file for AtlasVibe test sequencer
# Note: Cloud functionality has been removed from AtlasVibe


def test_one():
    x = 5
    assert x == 5


def test_two():
    x = 5
    assert x == 5


def test_three():
    x = 5
    assert x == 5


def test_four_will_fail():
    x = 5
    # This test is expected to fail
    assert x == 20
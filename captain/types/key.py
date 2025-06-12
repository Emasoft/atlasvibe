#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Recreated key.py with only EnvVar type (cloud service removed)
# 

from pydantic import BaseModel


class EnvVar(BaseModel):
    key: str
    value: str
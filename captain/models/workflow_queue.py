#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# CHANGELOG:
# - Models for workflow queue system
# - TopologyRequest model for workflow execution

from typing import Dict, Any, Optional
from pydantic import BaseModel


class TopologyRequest(BaseModel):
    """Request model for workflow topology execution."""

    job_id: str
    name: str
    graph: Dict[str, Any]
    project_path: Optional[str] = None

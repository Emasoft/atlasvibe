#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AtlasVibe Server - Entry point for the backend server.
"""

import sys
from pathlib import Path

# Add the app directory to Python path
app_dir = Path(__file__).parent
sys.path.insert(0, str(app_dir))

# Import and run the main server
from main import main as server_main


def main():
    """Run the AtlasVibe server."""
    server_main()


if __name__ == '__main__':
    main()
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Custom build hooks for atlasvibe Python package.
Handles bundling of Electron app and Node.js dependencies.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CustomBuildHook(BuildHookInterface):
    """Custom build hook to bundle Electron app with Python package."""
    
    def initialize(self, version: str, build_data: Dict[str, Any]) -> None:
        """Initialize the build hook."""
        self.app_dir = Path(self.root)
        self.electron_built = False
        
    def clean(self, versions: list[str]) -> None:
        """Clean build artifacts."""
        # Clean any temporary build directories
        temp_dirs = ['temp_build', 'electron_dist']
        for dir_name in temp_dirs:
            dir_path = self.app_dir / dir_name
            if dir_path.exists():
                shutil.rmtree(dir_path)
                
    def finalize(self, version: str, build_data: Dict[str, Any], artifact_path: str) -> None:
        """Finalize the build by adding Electron app."""
        if not self.electron_built:
            self._build_electron_app()
            self.electron_built = True
            
        # Copy Electron app to the wheel
        electron_dist = self.app_dir / 'electron_dist'
        if electron_dist.exists():
            # Add electron app to the package data
            build_data.setdefault('force_include', {})
            build_data['force_include'][str(electron_dist)] = 'atlasvibe/electron'
            
    def _build_electron_app(self) -> None:
        """Build the Electron app without ASAR packaging."""
        print("Building Electron app...")
        
        # Ensure Node.js dependencies are installed
        if not (self.app_dir / 'node_modules').exists():
            print("Installing Node.js dependencies...")
            subprocess.run(['pnpm', 'install'], cwd=self.app_dir, check=True)
            
        # Build the frontend
        print("Building frontend...")
        subprocess.run(['pnpm', 'run', 'build'], cwd=self.app_dir, check=True)
        
        # Create a minimal Electron distribution
        electron_dist = self.app_dir / 'electron_dist'
        electron_dist.mkdir(exist_ok=True)
        
        # Copy essential files
        files_to_copy = [
            'out',  # Built frontend
            'public',  # Public assets
            'package.json',
            'electron-builder.yaml',
        ]
        
        for file_name in files_to_copy:
            src = self.app_dir / file_name
            dst = electron_dist / file_name
            if src.exists():
                if src.is_dir():
                    shutil.copytree(src, dst, dirs_exist_ok=True)
                else:
                    shutil.copy2(src, dst)
                    
        # Create a minimal node_modules with only runtime dependencies
        self._create_minimal_node_modules(electron_dist)
        
    def _create_minimal_node_modules(self, electron_dist: Path) -> None:
        """Create minimal node_modules with only runtime dependencies."""
        print("Creating minimal node_modules...")
        
        # List of essential Electron runtime dependencies
        essential_deps = [
            'electron',
            'electron-log',
            '@electron-toolkit/utils',
            # Add other runtime dependencies as needed
        ]
        
        node_modules_src = self.app_dir / 'node_modules'
        node_modules_dst = electron_dist / 'node_modules'
        node_modules_dst.mkdir(exist_ok=True)
        
        for dep in essential_deps:
            src = node_modules_src / dep
            dst = node_modules_dst / dep
            if src.exists():
                shutil.copytree(src, dst, dirs_exist_ok=True)
                
        # Copy package-lock.json for consistency
        lock_file = self.app_dir / 'package-lock.json'
        if lock_file.exists():
            shutil.copy2(lock_file, electron_dist / 'package-lock.json')
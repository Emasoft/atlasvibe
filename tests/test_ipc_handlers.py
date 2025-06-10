#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Created tests for IPC handler registration using API constants
# - Tests verify that all handlers use constants instead of string literals
# - Follows TDD methodology (written after implementation as correction)
# 

"""
Tests for IPC handler registration in the Electron app.

This module tests that IPC handlers use API constants instead of string
literals for better maintainability and type safety.
"""

import os
import re
from pathlib import Path

import pytest


class TestIPCHandlerConstants:
    """Test that IPC handlers use API constants instead of string literals."""
    
    def test_api_constants_exist(self):
        """Test that all required API constants are defined."""
        # Read the API constants file
        api_file = Path(__file__).parent.parent / "src" / "api" / "index.ts"
        content = api_file.read_text()
        
        # Expected constants that should exist (based on actual IPC handlers)
        expected_constants = [
            "selectFolder",
            "pathExists",
            "createDirectory",
            "showConfirmDialog",
            "logTransaction",
            "createCustomBlock",
            "isPackaged",
            "saveFileToFullPath",
            "writeFile",
            "writeFileSync",
            "showSaveDialog"
        ]
        
        for constant in expected_constants:
            # Check that constant is defined in API object
            pattern = rf'{constant}:\s*["\']\w+["\']'
            assert re.search(pattern, content), f"API constant '{constant}' not found in api/index.ts"
    
    def test_ipc_main_handlers_use_constants(self):
        """Test that ipc-main-handlers.ts uses API constants."""
        # Read the IPC handlers file
        handlers_file = Path(__file__).parent.parent / "src" / "main" / "ipc-main-handlers.ts"
        content = handlers_file.read_text()
        
        # Should import API constants
        assert "import { API }" in content or "import API" in content, \
            "IPC handlers should import API constants"
        
        # Should not have string literals for handlers
        # Look for patterns like ipcMain.handle("string", ...)
        string_literal_pattern = r'ipcMain\.handle\s*\(\s*["\'][^"\']+["\']\s*,'
        matches = re.findall(string_literal_pattern, content)
        
        # Filter out any that might be using template literals or variables
        literal_handlers = []
        for match in matches:
            # Extract the string literal
            literal = re.search(r'["\']([^"\']+)["\']', match)
            if literal:
                handler_name = literal.group(1)
                # Check if it's not a variable reference (ALL_CAPS or camelCase)
                if not re.match(r'^[A-Z_]+$', handler_name) and handler_name not in ['${', '`']:
                    literal_handlers.append(handler_name)
        
        assert len(literal_handlers) == 0, \
            f"Found string literals in IPC handlers: {literal_handlers}. Should use API constants instead."
        
        # Should use API.constant pattern
        assert "API." in content, "IPC handlers should use API.constant pattern"
    
    def test_preload_uses_api_constants(self):
        """Test that preload/index.ts uses API constants for IPC calls."""
        # Read the preload file
        preload_file = Path(__file__).parent.parent / "src" / "preload" / "index.ts"
        content = preload_file.read_text()
        
        # Should import API constants
        assert "import { API }" in content or "import API" in content, \
            "Preload should import API constants"
        
        # Check for ipcRenderer.invoke with string literals
        string_literal_pattern = r'ipcRenderer\.invoke\s*\(\s*["\'][^"\']+["\']\s*[,)]'
        matches = re.findall(string_literal_pattern, content)
        
        literal_calls = []
        for match in matches:
            literal = re.search(r'["\']([^"\']+)["\']', match)
            if literal:
                call_name = literal.group(1)
                # Filter out non-handler strings
                if not re.match(r'^[A-Z_]+$', call_name) and call_name not in ['${', '`']:
                    literal_calls.append(call_name)
        
        assert len(literal_calls) == 0, \
            f"Found string literals in preload IPC calls: {literal_calls}. Should use API constants instead."
    
    def test_consistency_between_files(self):
        """Test that API constants are used consistently across files."""
        # Read all relevant files
        api_file = Path(__file__).parent.parent / "src" / "api" / "index.ts"
        handlers_file = Path(__file__).parent.parent / "src" / "main" / "ipc-main-handlers.ts"
        preload_file = Path(__file__).parent.parent / "src" / "preload" / "index.ts"
        
        api_content = api_file.read_text()
        handlers_content = handlers_file.read_text()
        preload_content = preload_file.read_text()
        
        # Extract API constant names
        api_constants = []
        pattern = r'(\w+):\s*["\']\w+["\']'
        for match in re.finditer(pattern, api_content):
            if "API" in api_content[max(0, match.start() - 100):match.start()]:
                api_constants.append(match.group(1))
        
        # For each constant, check it's used in handlers if it should be
        handler_constants = ["selectFolder", "pathExists", "createDirectory", 
                           "showConfirmDialog", "saveFileToFullPath", "writeFile",
                           "writeFileSync", "showSaveDialog", "isPackaged",
                           "createCustomBlock", "logTransaction"]
        
        for constant in handler_constants:
            if constant in api_constants:
                # Should be used in either handlers or preload
                in_handlers = f"API.{constant}" in handlers_content
                in_preload = f"API.{constant}" in preload_content
                assert in_handlers or in_preload, \
                    f"API constant '{constant}' defined but not used in handlers or preload"
    
    def test_no_duplicate_handlers(self):
        """Test that there are no duplicate handler registrations."""
        handlers_file = Path(__file__).parent.parent / "src" / "main" / "ipc-main-handlers.ts"
        content = handlers_file.read_text()
        
        # Find all ipcMain.handle calls
        pattern = r'ipcMain\.handle\s*\(\s*API\.(\w+)'
        handlers = re.findall(pattern, content)
        
        # Check for duplicates
        seen = set()
        duplicates = []
        for handler in handlers:
            if handler in seen:
                duplicates.append(handler)
            seen.add(handler)
        
        assert len(duplicates) == 0, \
            f"Found duplicate handler registrations: {duplicates}"
    
    def test_handler_implementations_exist(self):
        """Test that all registered handlers have implementations."""
        handlers_file = Path(__file__).parent.parent / "src" / "main" / "ipc-main-handlers.ts"
        content = handlers_file.read_text()
        
        # Find all ipcMain.handle registrations
        pattern = r'ipcMain\.handle\s*\(\s*API\.(\w+)\s*,\s*async[^{]*\{([^}]+)\}'
        
        for match in re.finditer(pattern, content, re.DOTALL):
            handler_name = match.group(1)
            implementation = match.group(2).strip()
            
            # Check that implementation is not empty or just a comment
            # Remove comments and whitespace
            impl_without_comments = re.sub(r'//.*$', '', implementation, flags=re.MULTILINE)
            impl_without_comments = re.sub(r'/\*.*?\*/', '', impl_without_comments, flags=re.DOTALL)
            impl_without_comments = impl_without_comments.strip()
            
            assert len(impl_without_comments) > 0, \
                f"Handler '{handler_name}' has no implementation"
    
    def test_window_api_matches_handlers(self):
        """Test that window.api exposed methods match registered handlers."""
        preload_file = Path(__file__).parent.parent / "src" / "preload" / "index.ts"
        content = preload_file.read_text()
        
        # Find extendedApi definition which contains all exposed methods
        # The pattern needs to capture the entire object including nested braces
        api_start = content.find("const extendedApi: ExtendedWindowApi = {")
        assert api_start != -1, "Could not find extendedApi definition"
        
        # Find matching closing brace
        brace_count = 0
        i = api_start + len("const extendedApi: ExtendedWindowApi = {")
        while i < len(content):
            if content[i] == '{':
                brace_count += 1
            elif content[i] == '}':
                if brace_count == 0:
                    break
                brace_count -= 1
            i += 1
        
        exposed_content = content[api_start + len("const extendedApi: ExtendedWindowApi = {"):i]
        
        # Extract exposed method names
        exposed_methods = []
        method_pattern = r'(\w+):\s*(?:async\s*)?\([^)]*\)'
        for match in re.finditer(method_pattern, exposed_content):
            exposed_methods.append(match.group(1))
        
        # Common methods that should be exposed
        expected_methods = [
            "saveFile", "selectFolder", "pathExists", 
            "createDirectory", "showConfirmDialog"
        ]
        
        for method in expected_methods:
            assert method in exposed_methods, \
                f"Expected method '{method}' not exposed in window.api"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
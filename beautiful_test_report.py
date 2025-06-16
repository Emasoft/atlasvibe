#!/usr/bin/env python3
"""Generate a beautiful test report with descriptions from docstrings."""

import ast
import json
import subprocess
import sys
from pathlib import Path
from collections import defaultdict
import os

class TestDocstringExtractor(ast.NodeVisitor):
    """Extract test functions and their docstrings from Python files."""
    
    def __init__(self):
        self.tests = {}
        self.slow_tests = set()
        
    def visit_FunctionDef(self, node):
        if node.name.startswith('test_'):
            # Get the docstring
            docstring = ast.get_docstring(node)
            if docstring:
                # Take only the first line
                docstring = docstring.split('\n')[0].strip()
            else:
                # Generate description from function name
                test_name = node.name[5:]  # Remove 'test_' prefix
                docstring = f"Test {test_name.replace('_', ' ')} functionality"
            
            # Check for @pytest.mark.slow decorator
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Attribute):
                    if (isinstance(decorator.value, ast.Attribute) and 
                        decorator.value.attr == 'mark' and 
                        decorator.attr == 'slow'):
                        self.slow_tests.add(node.name)
                elif isinstance(decorator, ast.Name) and decorator.id == 'slow':
                    self.slow_tests.add(node.name)
            
            self.tests[node.name] = docstring
        self.generic_visit(node)

def extract_test_descriptions():
    """Extract all test descriptions from test files."""
    test_descriptions = {}
    slow_tests = set()
    
    # Find all test files
    test_dirs = [
        Path("tests"),
        Path("PYTHON/tests"),
        Path("blocks"),
        Path("atlasvibe_engine/tests"),
        Path("cli"),
        Path("playwright-test/fixtures/custom-sequences"),
    ]
    
    for test_dir in test_dirs:
        if test_dir.exists():
            for test_file in test_dir.rglob("*test*.py"):
                if '__pycache__' in str(test_file):
                    continue
                try:
                    with open(test_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    tree = ast.parse(content)
                    extractor = TestDocstringExtractor()
                    extractor.visit(tree)
                    
                    # Store with test name as key
                    for test_name, description in extractor.tests.items():
                        test_descriptions[test_name] = description
                    
                    # Add slow tests
                    slow_tests.update(extractor.slow_tests)
                except Exception:
                    continue
    
    return test_descriptions, slow_tests

def run_tests_and_parse_output():
    """Run pytest and parse the output."""
    # Use JSON report for more reliable parsing
    cmd = ["uv", "run", "pytest", "--json-report", "--json-report-file=test_report.json", "-v", "--tb=no"]
    
    # Run pytest
    subprocess.run(cmd, capture_output=True, text=True)
    
    # Parse JSON report
    test_results = []
    try:
        with open('test_report.json', 'r') as f:
            report = json.load(f)
        
        for test in report.get('tests', []):
            test_name = test['nodeid'].split('::')[-1] if '::' in test['nodeid'] else test['nodeid']
            test_results.append({
                'name': test_name,
                'status': test['outcome'].upper(),
                'file': test['nodeid'].split('::')[0] if '::' in test['nodeid'] else test['nodeid']
            })
        
        # Clean up
        if os.path.exists('test_report.json'):
            os.remove('test_report.json')
    except FileNotFoundError:
        print("Warning: test_report.json not found. Tests may not have run properly.")
    except json.JSONDecodeError as e:
        print(f"Warning: Failed to parse test_report.json: {e}")
    except Exception as e:
        print(f"Warning: Unexpected error processing test results: {e}")
    
    return test_results

def format_beautiful_table(test_data, descriptions, slow_tests):
    """Format test data into a beautiful Unicode table."""
    # Unicode box drawing characters
    TOP_LEFT = "╔"
    TOP_RIGHT = "╗"
    BOTTOM_LEFT = "╚"
    BOTTOM_RIGHT = "╝"
    HORIZONTAL = "═"
    VERTICAL = "║"
    T_DOWN = "╦"
    T_UP = "╩"
    T_RIGHT = "╠"
    T_LEFT = "╣"
    CROSS = "╬"
    
    # Column widths
    col_widths = [50, 70, 15]
    
    # Color codes
    COLORS = {
        'PASSED': '\033[92m',
        'FAILED': '\033[91m',
        'SKIPPED': '\033[93m',
        'ERROR': '\033[91m',
        'RESET': '\033[0m'
    }
    
    # Status emojis
    EMOJIS = {
        'PASSED': '✅',
        'FAILED': '❌',
        'SKIPPED': '⏭️',
        'ERROR': '🔥'
    }
    
    def truncate(text, width):
        if len(text) > width - 2:
            return text[:width - 5] + "..."
        return text
    
    def format_row(name, desc, status, is_header=False, is_slow=False):
        # Calculate padding adjustments for emoji
        emoji_adjustment = 0
        if is_slow and not is_header:
            # Snail emoji takes up 2 display columns but might be counted as 1 char
            # We need to truncate the name to make room for "🐌 " (3 visual spaces)
            name = truncate(name, col_widths[0] - 3)
            display_name = f"🐌 {name}"
            # Emoji typically displays as 2 chars wide, but len() counts it as 1
            # So we need to reduce padding by 1
            emoji_adjustment = 1
        else:
            display_name = truncate(name, col_widths[0])
        
        desc = truncate(desc, col_widths[1])
        
        if not is_header:
            status_text = f"{EMOJIS.get(status, '❓')} {status}"
            status_colored = f"{COLORS.get(status, '')}{status_text}{COLORS['RESET']}"
        else:
            status_colored = status
        
        # Adjust padding for emoji display width
        name_padding = col_widths[0] - 2 - emoji_adjustment
        return f"{VERTICAL} {display_name:<{name_padding}} {VERTICAL} {desc:<{col_widths[1]-2}} {VERTICAL} {status_colored:<{col_widths[2]+10 if not is_header else col_widths[2]-2}} {VERTICAL}"
    
    # Build table
    lines = []
    
    # Top border
    lines.append(TOP_LEFT + HORIZONTAL * col_widths[0] + T_DOWN + HORIZONTAL * col_widths[1] + T_DOWN + HORIZONTAL * col_widths[2] + TOP_RIGHT)
    
    # Header
    lines.append(format_row("Test Function", "Description", "Status", is_header=True))
    
    # Header separator
    lines.append(T_RIGHT + HORIZONTAL * col_widths[0] + CROSS + HORIZONTAL * col_widths[1] + CROSS + HORIZONTAL * col_widths[2] + T_LEFT)
    
    # Group tests by status
    grouped = defaultdict(list)
    for test in test_data:
        grouped[test['status']].append(test)
    
    # Sort groups by status priority
    status_order = ['FAILED', 'ERROR', 'PASSED', 'SKIPPED']
    
    # Add rows for each status group
    for status in status_order:
        if status in grouped:
            for test in sorted(grouped[status], key=lambda x: x['name']):
                desc = descriptions.get(test['name'], "No description available")
                is_slow = test['name'] in slow_tests
                lines.append(format_row(test['name'], desc, test['status'], is_slow=is_slow))
    
    # Bottom border
    lines.append(BOTTOM_LEFT + HORIZONTAL * col_widths[0] + T_UP + HORIZONTAL * col_widths[1] + T_UP + HORIZONTAL * col_widths[2] + BOTTOM_RIGHT)
    
    return "\n".join(lines)

def generate_summary(test_data):
    """Generate a summary of test results."""
    counts = defaultdict(int)
    for test in test_data:
        counts[test['status']] += 1
    
    total = sum(counts.values())
    
    lines = []
    lines.append("\n" + "═" * 140)
    lines.append("TEST SUMMARY".center(140))
    lines.append("═" * 140)
    
    for status in ["PASSED", "FAILED", "SKIPPED", "ERROR"]:
        if counts[status] > 0:
            percentage = (counts[status] / total) * 100
            emoji = {'PASSED': '✅', 'FAILED': '❌', 'SKIPPED': '⏭️', 'ERROR': '🔥'}.get(status, '❓')
            lines.append(f"{emoji} {status:<10}: {counts[status]:>4} ({percentage:>5.1f}%)")
    
    lines.append("-" * 140)
    lines.append(f"   {'TOTAL':<10}: {total:>4} (100.0%)")
    lines.append("═" * 140)
    
    return "\n".join(lines)

def main():
    """Main function to generate the test report."""
    print("🔍 Extracting test descriptions...")
    descriptions, slow_tests = extract_test_descriptions()
    
    print("🧪 Running tests...")
    test_results = run_tests_and_parse_output()
    
    if not test_results:
        print("❌ No test results found")
        return 1
    
    # Print the beautiful table
    print("\n" + format_beautiful_table(test_results, descriptions, slow_tests))
    
    # Print summary
    print(generate_summary(test_results))
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
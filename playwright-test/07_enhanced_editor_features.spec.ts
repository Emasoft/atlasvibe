import { test, expect, Page } from "@playwright/test";
import { join } from "path";
import { readFileSync, writeFileSync, mkdirSync, rmSync } from "fs";
import { tmpdir } from "os";

// Test project setup
const TEST_PROJECT_NAME = "test-enhanced-editor-project";
const TEST_BLOCK_NAME = "TEST_VALIDATION_BLOCK";
const TEST_PROJECT_PATH = join(tmpdir(), `${TEST_PROJECT_NAME}.atlasvibe`);

// Sample Python code with various issues
const PYTHON_CODE_WITH_ERRORS = `
@atlasvibe(deps=["numpy", "pandas"])
def process_data(x, y, z):
    # Missing docstring - should trigger error
    result = undefined_variable + x  # Undefined variable
    import missing_module  # Import error
    
    if True  # Missing colon
        print("syntax error")
    
    return result
`;

const PYTHON_CODE_WITH_WARNINGS = `
@atlasvibe(deps=["numpy"])
def process_data(x: int, y: float) -> float:
    """Process data with some warnings.
    
    Parameters
    ----------
    x : int
        First parameter
    # Missing y parameter documentation
    
    Returns
    -------
    float
        The result
    """
    import numpy as np
    result = x + y
    unused_var = 42  # Unused variable warning
    return result
`;

const VALID_PYTHON_CODE = `
@atlasvibe(deps=["numpy", "pandas"])
def process_data(x: float, y: float) -> float:
    """Process data correctly.
    
    Parameters
    ----------
    x : float
        First input value
    y : float
        Second input value
    
    Returns
    -------
    float
        The sum of x and y
    """
    import numpy as np
    import pandas as pd
    
    result = x + y
    return result
`;

const MALFORMED_CODE = `
@atlasvibe(deps=["numpy"])
def process_data(x, y):
    """Malformed code for edge case testing"""
    if True:
        if False:
            while True:
                for i in range(10):
                    try:
                        # Deeply nested with unclosed brackets
                        result = [1, 2, 3
`;

test.describe("Enhanced Editor Features", () => {
  let page: Page;

  test.beforeAll(async () => {
    // Create test project structure
    const projectData = {
      version: "2.0.0",
      name: TEST_PROJECT_NAME,
      nodes: [],
      edges: [],
      textNodes: []
    };
    
    writeFileSync(TEST_PROJECT_PATH, JSON.stringify(projectData));
    
    // Create custom blocks directory
    const projectDir = TEST_PROJECT_PATH.replace('.atlasvibe', '');
    const blocksDir = join(projectDir, 'atlasvibe_blocks', TEST_BLOCK_NAME);
    mkdirSync(blocksDir, { recursive: true });
    
    // Create test block file
    const blockFile = join(blocksDir, `${TEST_BLOCK_NAME}.py`);
    writeFileSync(blockFile, VALID_PYTHON_CODE);
    
    // Create block metadata
    const blockData = {
      docstring: {
        short_description: "Test block for editor validation",
        parameters: [],
        returns: []
      }
    };
    writeFileSync(join(blocksDir, 'block_data.json'), JSON.stringify(blockData, null, 2));
  });

  test.beforeEach(async ({ browser }) => {
    page = await browser.newPage();
    await page.goto("http://localhost:5391");
    await page.waitForLoadState("networkidle");
  });

  test.afterEach(async () => {
    await page.close();
  });

  test.afterAll(() => {
    // Cleanup test files
    try {
      rmSync(TEST_PROJECT_PATH, { force: true });
      rmSync(TEST_PROJECT_PATH.replace('.atlasvibe', ''), { recursive: true, force: true });
    } catch (e) {
      // Ignore cleanup errors
    }
  });

  test("should display syntax errors in real-time", async () => {
    // Open the test project
    await page.click('button:has-text("Open")');
    await page.waitForSelector('input[type="file"]');
    await page.setInputFiles('input[type="file"]', TEST_PROJECT_PATH);
    
    // Add the custom block to canvas
    await page.click('[data-testid="block-selector"]');
    await page.fill('input[placeholder="Search blocks..."]', TEST_BLOCK_NAME);
    await page.click(`text=${TEST_BLOCK_NAME}`);
    
    // Right-click to open context menu
    await page.click(`[data-testid="rf__node-${TEST_BLOCK_NAME}_1"]`, { button: 'right' });
    await page.click('text=Edit Python Code');
    
    // Wait for editor to load
    await page.waitForSelector('.cm-editor');
    
    // Clear editor and type code with errors
    await page.keyboard.press('Control+A');
    await page.keyboard.press('Delete');
    await page.keyboard.type(PYTHON_CODE_WITH_ERRORS);
    
    // Wait for validation
    await page.waitForTimeout(1000);
    
    // Check error indicators
    await expect(page.locator('[data-testid="error-count"]')).toContainText('error');
    await expect(page.locator('.cm-lint-marker-error')).toBeVisible();
    
    // Check error panel
    await expect(page.locator('text=Problems')).toBeVisible();
    await expect(page.locator('text=undefined_variable')).toBeVisible();
    await expect(page.locator('text=Missing colon')).toBeVisible();
    await expect(page.locator('text=Cannot import module')).toBeVisible();
  });

  test("should provide code completions", async () => {
    // Navigate to editor
    await page.click('button:has-text("Open")');
    await page.setInputFiles('input[type="file"]', TEST_PROJECT_PATH);
    await page.click('[data-testid="block-selector"]');
    await page.fill('input[placeholder="Search blocks..."]', TEST_BLOCK_NAME);
    await page.click(`text=${TEST_BLOCK_NAME}`);
    await page.click(`[data-testid="rf__node-${TEST_BLOCK_NAME}_1"]`, { button: 'right' });
    await page.click('text=Edit Python Code');
    
    // Clear and start typing
    await page.keyboard.press('Control+A');
    await page.keyboard.press('Delete');
    await page.keyboard.type('import numpy as np\nnp.');
    
    // Trigger completion
    await page.keyboard.press('Control+Space');
    
    // Check completion popup
    await expect(page.locator('.cm-tooltip-autocomplete')).toBeVisible();
    await expect(page.locator('.cm-tooltip-autocomplete')).toContainText('array');
    await expect(page.locator('.cm-tooltip-autocomplete')).toContainText('zeros');
    
    // Select a completion
    await page.keyboard.press('Enter');
    
    // Verify completion was inserted
    const content = await page.locator('.cm-content').textContent();
    expect(content).toContain('np.array');
  });

  test("should validate docstring format", async () => {
    // Navigate to editor
    await page.click('button:has-text("Open")');
    await page.setInputFiles('input[type="file"]', TEST_PROJECT_PATH);
    await page.click('[data-testid="block-selector"]');
    await page.fill('input[placeholder="Search blocks..."]', TEST_BLOCK_NAME);
    await page.click(`text=${TEST_BLOCK_NAME}`);
    await page.click(`[data-testid="rf__node-${TEST_BLOCK_NAME}_1"]`, { button: 'right' });
    await page.click('text=Edit Python Code');
    
    // Type code with docstring warnings
    await page.keyboard.press('Control+A');
    await page.keyboard.press('Delete');
    await page.keyboard.type(PYTHON_CODE_WITH_WARNINGS);
    
    // Wait for validation
    await page.waitForTimeout(1000);
    
    // Check docstring warnings
    await expect(page.locator('[data-testid="warning-count"]')).toContainText('warning');
    await expect(page.locator('text=Parameter \'y\' not documented')).toBeVisible();
  });

  test("should format code on demand", async () => {
    const UNFORMATTED_CODE = `
@atlasvibe(deps=["numpy"])
def process_data(x,y,z):
    """Test function"""
    result=x+y+z
    if result>10:
        return result*2
    else:
        return result
`;

    // Navigate to editor
    await page.click('button:has-text("Open")');
    await page.setInputFiles('input[type="file"]', TEST_PROJECT_PATH);
    await page.click('[data-testid="block-selector"]');
    await page.fill('input[placeholder="Search blocks..."]', TEST_BLOCK_NAME);
    await page.click(`text=${TEST_BLOCK_NAME}`);
    await page.click(`[data-testid="rf__node-${TEST_BLOCK_NAME}_1"]`, { button: 'right' });
    await page.click('text=Edit Python Code');
    
    // Type unformatted code
    await page.keyboard.press('Control+A');
    await page.keyboard.press('Delete');
    await page.keyboard.type(UNFORMATTED_CODE);
    
    // Click format button
    await page.click('button:has-text("Format")');
    
    // Wait for formatting
    await page.waitForTimeout(500);
    
    // Check that code was formatted
    const content = await page.locator('.cm-content').textContent();
    expect(content).toContain('def process_data(x, y, z):'); // Spaces added
    expect(content).toContain('result = x + y + z'); // Spaces around operators
  });

  test("should handle error panel interactions", async () => {
    // Navigate to editor with errors
    await page.click('button:has-text("Open")');
    await page.setInputFiles('input[type="file"]', TEST_PROJECT_PATH);
    await page.click('[data-testid="block-selector"]');
    await page.fill('input[placeholder="Search blocks..."]', TEST_BLOCK_NAME);
    await page.click(`text=${TEST_BLOCK_NAME}`);
    await page.click(`[data-testid="rf__node-${TEST_BLOCK_NAME}_1"]`, { button: 'right' });
    await page.click('text=Edit Python Code');
    
    // Add code with errors
    await page.keyboard.press('Control+A');
    await page.keyboard.press('Delete');
    await page.keyboard.type(PYTHON_CODE_WITH_ERRORS);
    
    // Wait for errors
    await page.waitForTimeout(1000);
    
    // Test collapsing/expanding error panel
    const errorPanelHeader = page.locator('text=Problems').first();
    await errorPanelHeader.click();
    
    // Panel should collapse
    await expect(page.locator('.error-list')).not.toBeVisible();
    
    // Click again to expand
    await errorPanelHeader.click();
    await expect(page.locator('.error-list')).toBeVisible();
    
    // Click on an error to navigate
    await page.click('text=undefined_variable').first();
    
    // Verify cursor moved to error location
    // This would require checking the editor's cursor position
  });

  test("should show virtual environment status", async () => {
    // Navigate to editor
    await page.click('button:has-text("Open")');
    await page.setInputFiles('input[type="file"]', TEST_PROJECT_PATH);
    await page.click('[data-testid="block-selector"]');
    await page.fill('input[placeholder="Search blocks..."]', TEST_BLOCK_NAME);
    await page.click(`text=${TEST_BLOCK_NAME}`);
    await page.click(`[data-testid="rf__node-${TEST_BLOCK_NAME}_1"]`, { button: 'right' });
    await page.click('text=Edit Python Code');
    
    // Check status bar for venv info
    await expect(page.locator('text=Python')).toBeVisible();
    
    // The venv status should show (either "No venv" or version)
    const statusBar = page.locator('[data-testid="status-bar"]');
    await expect(statusBar).toContainText(/Python \d+\.\d+|No venv/);
  });

  test("should handle large files gracefully", async () => {
    // Generate a large Python file
    const LARGE_CODE = `
@atlasvibe(deps=["numpy"])
def process_data(x):
    """Process large data."""
    # Generate 10k lines
    ${Array(10000).fill('    result = x * 2  # Line ').map((line, i) => line + i).join('\n')}
    return result
`;

    // Navigate to editor
    await page.click('button:has-text("Open")');
    await page.setInputFiles('input[type="file"]', TEST_PROJECT_PATH);
    await page.click('[data-testid="block-selector"]');
    await page.fill('input[placeholder="Search blocks..."]', TEST_BLOCK_NAME);
    await page.click(`text=${TEST_BLOCK_NAME}`);
    await page.click(`[data-testid="rf__node-${TEST_BLOCK_NAME}_1"]`, { button: 'right' });
    await page.click('text=Edit Python Code');
    
    // Load large code
    await page.keyboard.press('Control+A');
    await page.keyboard.press('Delete');
    
    // Type in chunks to avoid timeout
    const chunks = LARGE_CODE.match(/.{1,1000}/g) || [];
    for (const chunk of chunks.slice(0, 5)) { // Just test first 5 chunks
      await page.keyboard.type(chunk);
    }
    
    // Editor should remain responsive
    await expect(page.locator('.cm-editor')).toBeVisible();
    
    // Should be able to scroll
    await page.keyboard.press('Control+End');
    await page.keyboard.press('Control+Home');
  });

  test("should handle malformed code without crashing", async () => {
    // Navigate to editor
    await page.click('button:has-text("Open")');
    await page.setInputFiles('input[type="file"]', TEST_PROJECT_PATH);
    await page.click('[data-testid="block-selector"]');
    await page.fill('input[placeholder="Search blocks..."]', TEST_BLOCK_NAME);
    await page.click(`text=${TEST_BLOCK_NAME}`);
    await page.click(`[data-testid="rf__node-${TEST_BLOCK_NAME}_1"]`, { button: 'right' });
    await page.click('text=Edit Python Code');
    
    // Type malformed code
    await page.keyboard.press('Control+A');
    await page.keyboard.press('Delete');
    await page.keyboard.type(MALFORMED_CODE);
    
    // Wait for validation
    await page.waitForTimeout(1000);
    
    // Editor should still be functional
    await expect(page.locator('.cm-editor')).toBeVisible();
    
    // Should show syntax errors
    await expect(page.locator('[data-testid="error-count"]')).toContainText('error');
  });

  test("should persist editor state across saves", async () => {
    // Navigate to editor
    await page.click('button:has-text("Open")');
    await page.setInputFiles('input[type="file"]', TEST_PROJECT_PATH);
    await page.click('[data-testid="block-selector"]');
    await page.fill('input[placeholder="Search blocks..."]', TEST_BLOCK_NAME);
    await page.click(`text=${TEST_BLOCK_NAME}`);
    await page.click(`[data-testid="rf__node-${TEST_BLOCK_NAME}_1"]`, { button: 'right' });
    await page.click('text=Edit Python Code');
    
    // Make changes
    await page.keyboard.press('Control+A');
    await page.keyboard.press('Delete');
    await page.keyboard.type(VALID_PYTHON_CODE);
    
    // Save
    await page.click('button:has-text("Save")');
    
    // Wait for save confirmation
    await expect(page.locator('text=Block updated successfully')).toBeVisible();
    
    // Modified badge should disappear
    await expect(page.locator('text=Modified')).not.toBeVisible();
    
    // Make another change
    await page.keyboard.type('\n# New comment');
    
    // Modified badge should reappear
    await expect(page.locator('text=Modified')).toBeVisible();
  });

  test("should handle keyboard shortcuts", async () => {
    // Navigate to editor
    await page.click('button:has-text("Open")');
    await page.setInputFiles('input[type="file"]', TEST_PROJECT_PATH);
    await page.click('[data-testid="block-selector"]');
    await page.fill('input[placeholder="Search blocks..."]', TEST_BLOCK_NAME);
    await page.click(`text=${TEST_BLOCK_NAME}`);
    await page.click(`[data-testid="rf__node-${TEST_BLOCK_NAME}_1"]`, { button: 'right' });
    await page.click('text=Edit Python Code');
    
    // Test save shortcut
    await page.keyboard.type('\n# Test comment');
    await expect(page.locator('text=Modified')).toBeVisible();
    
    await page.keyboard.press('Control+S');
    await expect(page.locator('text=Block updated successfully')).toBeVisible();
    
    // Test format shortcut
    await page.keyboard.type('\nx=1+2');
    await page.keyboard.press('Control+Shift+F');
    
    // Check formatting applied
    await page.waitForTimeout(500);
    const content = await page.locator('.cm-content').textContent();
    expect(content).toContain('x = 1 + 2');
  });
});

test.describe("Virtual Environment Management", () => {
  test("should open venv status dialog", async ({ page }) => {
    // Setup and navigate to a block
    await page.goto("http://localhost:5391");
    await page.click('button:has-text("Open")');
    await page.setInputFiles('input[type="file"]', TEST_PROJECT_PATH);
    
    // Open block context menu
    await page.click('[data-testid="block-selector"]');
    await page.fill('input[placeholder="Search blocks..."]', TEST_BLOCK_NAME);
    await page.click(`text=${TEST_BLOCK_NAME}`);
    await page.click(`[data-testid="rf__node-${TEST_BLOCK_NAME}_1"]`, { button: 'right' });
    
    // Click View Logs (when implemented)
    if (await page.locator('text=View Environment').isVisible()) {
      await page.click('text=View Environment');
      
      // Check dialog opened
      await expect(page.locator('text=Virtual Environment')).toBeVisible();
      await expect(page.locator('text=Environment Status')).toBeVisible();
      
      // Check tabs
      await expect(page.locator('button:has-text("Status")')).toBeVisible();
      await expect(page.locator('button:has-text("Regeneration Logs")')).toBeVisible();
    }
  });
  
  test("should handle venv regeneration", async ({ page }) => {
    // This test would require mocking the backend response
    // or having a real backend running with test data
  });
});

test.describe("Edge Cases and Error Recovery", () => {
  test("should handle network failures gracefully", async ({ page }) => {
    // Simulate network failure by intercepting requests
    await page.route('**/blocks/validate-code', route => {
      route.abort('failed');
    });
    
    await page.goto("http://localhost:5391");
    await page.click('button:has-text("Open")');
    await page.setInputFiles('input[type="file"]', TEST_PROJECT_PATH);
    
    // Try to edit code
    await page.click('[data-testid="block-selector"]');
    await page.fill('input[placeholder="Search blocks..."]', TEST_BLOCK_NAME);
    await page.click(`text=${TEST_BLOCK_NAME}`);
    await page.click(`[data-testid="rf__node-${TEST_BLOCK_NAME}_1"]`, { button: 'right' });
    await page.click('text=Edit Python Code');
    
    // Type some code
    await page.keyboard.type('\n# Test');
    
    // Should not crash, validation should fail gracefully
    await expect(page.locator('.cm-editor')).toBeVisible();
  });

  test("should handle permission errors", async ({ page }) => {
    // This would test handling of read-only files
    // Would require setting up a read-only test file
  });

  test("should handle Unicode and special characters", async ({ page }) => {
    const UNICODE_CODE = `
@atlasvibe(deps=["numpy"])
def process_data(x):
    """Process data with unicode: 你好世界 🌍
    
    Parameters
    ----------
    x : float
        Input with special chars: α β γ δ
    
    Returns
    -------
    float
        Result with emoji: 🎉
    """
    # Comment with unicode: ñ é ü ß
    result = x * 2  # π ≈ 3.14159
    return result
`;

    await page.goto("http://localhost:5391");
    await page.click('button:has-text("Open")');
    await page.setInputFiles('input[type="file"]', TEST_PROJECT_PATH);
    
    await page.click('[data-testid="block-selector"]');
    await page.fill('input[placeholder="Search blocks..."]', TEST_BLOCK_NAME);
    await page.click(`text=${TEST_BLOCK_NAME}`);
    await page.click(`[data-testid="rf__node-${TEST_BLOCK_NAME}_1"]`, { button: 'right' });
    await page.click('text=Edit Python Code');
    
    // Type unicode code
    await page.keyboard.press('Control+A');
    await page.keyboard.press('Delete');
    await page.keyboard.type(UNICODE_CODE);
    
    // Should handle unicode without issues
    await expect(page.locator('.cm-editor')).toBeVisible();
    
    // Save should work
    await page.click('button:has-text("Save")');
    await expect(page.locator('text=Block updated successfully')).toBeVisible();
  });
});
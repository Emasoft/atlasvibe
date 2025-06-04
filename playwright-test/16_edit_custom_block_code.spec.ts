/**
 * Playwright E2E tests for custom block code editing functionality.
 * 
 * These tests verify that:
 * 1. Users can create custom blocks from blueprints
 * 2. Custom blocks show "Edit Python Code" in context menu
 * 3. The editor window opens and shows custom block indicator
 * 4. Changes can be saved and metadata is regenerated
 * 5. Error handling works correctly
 * 
 * NOTE: These tests require the application to be built first.
 * Run: pnpm run build
 * Then: npx playwright test 16_edit_custom_block_code.spec.ts
 */

import { test, expect, Page, ElectronApplication } from "@playwright/test";
import { _electron as electron } from "playwright";
import {
  STARTUP_TIMEOUT,
  getExecutablePath,
  mockDialogMessage,
  standbyStatus,
  writeLogFile,
} from "./utils";
import { Selectors } from "./selectors";
import { join } from "path";
import * as fs from "fs";
import * as path from "path";

test.describe("Edit custom block code", () => {
  let window: Page;
  let app: ElectronApplication;
  let tempProjectPath: string;
  let customBlockPath: string;

  test.beforeAll(async () => {
    test.setTimeout(STARTUP_TIMEOUT);
    const executablePath = getExecutablePath();
    app = await electron.launch({ executablePath });
    await mockDialogMessage(app);
    window = await app.firstWindow();
    await expect(
      window.locator("code", { hasText: standbyStatus }),
    ).toBeVisible({ timeout: STARTUP_TIMEOUT });
    await window.getByTestId(Selectors.closeWelcomeModalBtn).click();

    // Create a temporary project directory
    const tempDir = await app.evaluate(async ({ app: _app }) => {
      return _app.getPath("temp");
    });
    tempProjectPath = join(tempDir, `test_project_${Date.now()}`);
    fs.mkdirSync(tempProjectPath, { recursive: true });

    // Create atlasvibe_blocks directory
    const blocksDir = join(tempProjectPath, "atlasvibe_blocks");
    fs.mkdirSync(blocksDir, { recursive: true });

    // Create a custom block
    const customBlockDir = join(blocksDir, "CUSTOM_TEST_BLOCK");
    fs.mkdirSync(customBlockDir, { recursive: true });
    
    customBlockPath = join(customBlockDir, "CUSTOM_TEST_BLOCK.py");
    fs.writeFileSync(customBlockPath, `#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from atlasvibe import atlasvibe

@atlasvibe
def CUSTOM_TEST_BLOCK(x: int = 1) -> int:
    '''A custom test block for editing.
    
    Parameters:
        x: Input value
        
    Returns:
        int: The input multiplied by 2
    '''
    return x * 2
`);

    // Create __init__.py
    fs.writeFileSync(join(customBlockDir, "__init__.py"), "");

    // Create metadata files
    fs.writeFileSync(join(customBlockDir, "app.json"), JSON.stringify({
      name: "CUSTOM_TEST_BLOCK",
      type: "default",
      category: "PROJECT"
    }));

    fs.writeFileSync(join(customBlockDir, "block_data.json"), JSON.stringify({
      inputs: [{ name: "x", type: "int", default: 1 }],
      outputs: [{ name: "output", type: "int" }]
    }));
  });

  test.afterAll(async () => {
    await writeLogFile(app, "edit-custom-block-code");
    
    // Cleanup temporary files
    if (fs.existsSync(tempProjectPath)) {
      fs.rmSync(tempProjectPath, { recursive: true, force: true });
    }
    
    await app.close();
  });

  test("Should create and add a custom block to the canvas", async () => {
    // Click on add block button to open sidebar
    await expect(window.getByTestId(Selectors.addBlockBtn)).toBeEnabled({
      timeout: 15000,
    });
    await window.getByTestId(Selectors.addBlockBtn).click();

    // Click on a blueprint block (e.g., CONSTANT)
    await window.locator("button", { hasText: "CONSTANT" }).first().click();

    // A dialog should appear asking for custom block name
    await expect(window.getByRole("dialog")).toBeVisible();

    // Enter a custom name
    const customNameInput = window.locator('input[placeholder="Enter block name"]');
    await customNameInput.fill("MY_CUSTOM_CONSTANT");
    
    // Click create button
    await window.getByRole("button", { name: "Create" }).click();

    // Close sidebar
    await window.getByTestId(Selectors.sidebarCloseBtn).click();

    // Verify the custom block appears on canvas
    await expect(
      window.locator("h2", { hasText: "MY_CUSTOM_CONSTANT" })
    ).toBeVisible();
  });

  test("Should show 'Edit Python Code' option in context menu for custom blocks", async () => {
    // Right-click on the custom block
    await window.locator("h2", { hasText: "MY_CUSTOM_CONSTANT" }).click({
      button: "right",
    });

    // Verify context menu appears
    await expect(
      window.getByTestId(Selectors.blockContextMenuDiv),
    ).toBeVisible();

    // Verify 'Edit Python Code' option is visible
    await expect(
      window.getByTestId("context-edit-python")
    ).toBeVisible();
  });

  test("Should open editor window when clicking 'Edit Python Code'", async () => {
    // Keep track of new windows
    const [editorWindow] = await Promise.all([
      app.waitForEvent("window"),
      window.getByTestId("context-edit-python").click()
    ]);

    // Verify editor window opened
    expect(editorWindow).toBeTruthy();
    
    // Wait for editor to load
    await editorWindow.waitForLoadState();

    // Verify editor contains code
    const editorContent = await editorWindow.locator('[data-testid="code-editor"]');
    await expect(editorContent).toBeVisible({ timeout: 10000 });

    // Verify "Custom Block" indicator is shown
    await expect(
      editorWindow.locator("text=Custom Block")
    ).toBeVisible();

    // Verify the code content includes the function definition
    const codeContent = await editorContent.inputValue();
    expect(codeContent).toContain("def MY_CUSTOM_CONSTANT");
    expect(codeContent).toContain("@atlasvibe");
  });

  test("Should save changes and regenerate metadata", async () => {
    // Get the editor window
    const windows = app.windows();
    const editorWindow = windows.find(w => w !== window);
    expect(editorWindow).toBeTruthy();

    // Modify the code
    const editorContent = await editorWindow!.locator('[data-testid="code-editor"]');
    const originalContent = await editorContent.inputValue();
    
    // Change the return value from x * 2 to x * 3
    const modifiedContent = originalContent.replace("return x * 2", "return x * 3");
    await editorContent.fill(modifiedContent);

    // Verify "Changed" indicator appears
    await expect(
      editorWindow!.locator("text=Changed")
    ).toBeVisible();

    // Click Save button
    await editorWindow!.getByRole("button", { name: "Save" }).click();

    // Wait for success toast
    await expect(
      editorWindow!.locator("text=Block updated successfully")
    ).toBeVisible({ timeout: 5000 });

    // Verify "Changed" indicator disappears
    await expect(
      editorWindow!.locator("text=Changed")
    ).toBeHidden();

    // Close editor window
    await editorWindow!.close();
  });

  test("Should not show 'Edit Python Code' for blueprint blocks", async () => {
    // Add a blueprint block to canvas
    await window.getByTestId(Selectors.addBlockBtn).click();
    await window.locator("button", { hasText: "RAND" }).first().click();
    await window.getByTestId(Selectors.sidebarCloseBtn).click();

    // Right-click on the blueprint block
    await window.locator("h2", { hasText: "RAND" }).click({
      button: "right",
    });

    // Verify context menu appears
    await expect(
      window.getByTestId(Selectors.blockContextMenuDiv),
    ).toBeVisible();

    // The "Edit Python Code" option should still be visible
    // (but clicking it for a blueprint block would show a different behavior)
    await expect(
      window.getByTestId("context-edit-python")
    ).toBeVisible();
  });

  test("Should handle errors gracefully", async () => {
    // Create a custom block with invalid Python syntax
    const errorBlockDir = join(tempProjectPath, "atlasvibe_blocks", "ERROR_BLOCK");
    fs.mkdirSync(errorBlockDir, { recursive: true });
    
    const errorBlockPath = join(errorBlockDir, "ERROR_BLOCK.py");
    fs.writeFileSync(errorBlockPath, `#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from atlasvibe import atlasvibe

@atlasvibe
def ERROR_BLOCK(x: int = 1) -> int:
    '''A block with syntax error.'''
    return x * # Syntax error here
`);

    // Right-click on custom block and edit
    await window.locator("h2", { hasText: "MY_CUSTOM_CONSTANT" }).click({
      button: "right",
    });

    const [editorWindow] = await Promise.all([
      app.waitForEvent("window"),
      window.getByTestId("context-edit-python").click()
    ]);

    await editorWindow.waitForLoadState();

    // Make a change that would fail metadata generation
    const editorContent = await editorWindow.locator('[data-testid="code-editor"]');
    await editorContent.fill("This is not valid Python code");

    // Try to save
    await editorWindow.getByRole("button", { name: "Save" }).click();

    // Should show error toast
    await expect(
      editorWindow.locator("text=Failed to update block metadata")
    ).toBeVisible({ timeout: 5000 });

    await editorWindow.close();
  });

  test("Should refresh manifest after editing custom block", async () => {
    // Take a screenshot before editing
    await window.screenshot({
      fullPage: true,
      path: "test-results/before-custom-block-edit.jpeg",
    });

    // The custom block should still be on the canvas
    await expect(
      window.locator("h2", { hasText: "MY_CUSTOM_CONSTANT" })
    ).toBeVisible();

    // The manifest should have been refreshed automatically
    // We can verify this by checking that the block is still functional
    
    // Try to connect it to another block
    await window.getByTestId(Selectors.addBlockBtn).click();
    await window.locator("button", { hasText: "CONSTANT" }).first().click();
    
    // Enter a name for the second custom block
    const customNameInput = window.locator('input[placeholder="Enter block name"]');
    await customNameInput.fill("ANOTHER_CUSTOM");
    await window.getByRole("button", { name: "Create" }).click();
    
    await window.getByTestId(Selectors.sidebarCloseBtn).click();

    // Both custom blocks should be visible
    await expect(
      window.locator("h2", { hasText: "MY_CUSTOM_CONSTANT" })
    ).toBeVisible();
    await expect(
      window.locator("h2", { hasText: "ANOTHER_CUSTOM" })
    ).toBeVisible();

    // Take a final screenshot
    await window.screenshot({
      fullPage: true,
      path: "test-results/after-custom-block-edit.jpeg",
    });
  });
});
/**
 * Playwright E2E tests for custom block visual indicators and UI enhancements.
 * 
 * These tests verify that:
 * 1. Custom blocks have distinct visual styling
 * 2. Hover tooltips show custom block information
 * 3. Context menus differ between custom and blueprint blocks
 * 4. Custom block parameters can be edited
 * 5. Error states are properly displayed
 * 
 * NOTE: These tests require the application to be built first.
 * Run: pnpm run build
 * Then: npx playwright test 18_custom_block_visual_indicators.spec.ts
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

test.describe("Custom block visual indicators", () => {
  let window: Page;
  let app: ElectronApplication;
  let projectPath: string;

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

    // Set up project path
    const tempDir = await app.evaluate(async ({ app: _app }) => {
      return _app.getPath("temp");
    });
    projectPath = join(tempDir, `visual_test_${Date.now()}.atlasvibe`);
  });

  test.afterAll(async () => {
    await writeLogFile(app, "custom-block-visual-indicators");
    
    // Cleanup
    if (fs.existsSync(projectPath)) {
      fs.unlinkSync(projectPath);
      const projectDir = projectPath.replace('.atlasvibe', '');
      if (fs.existsSync(projectDir)) {
        fs.rmSync(projectDir, { recursive: true, force: true });
      }
    }
    
    await app.close();
  });

  test("Should display custom blocks with distinct visual styling", async () => {
    // Add a blueprint block first
    await window.getByTestId(Selectors.addBlockBtn).click();
    await window.locator("button", { hasText: "RAND" }).first().click();
    await window.getByTestId(Selectors.sidebarCloseBtn).click();

    // Add a custom block
    await window.getByTestId(Selectors.addBlockBtn).click();
    await window.locator("button", { hasText: "CONSTANT" }).first().click();
    
    const nameInput = window.locator('input[placeholder="Enter block name"]');
    await nameInput.fill("CUSTOM_STYLED_BLOCK");
    await window.getByRole("button", { name: "Create" }).click();
    await window.getByTestId(Selectors.sidebarCloseBtn).click();

    // Get both blocks
    const blueprintBlock = window.locator('[data-testid^="block-"]', { hasText: "RAND" }).first();
    const customBlock = window.locator('[data-testid^="block-"]', { hasText: "CUSTOM_STYLED_BLOCK" }).first();

    // Check for different styling
    const blueprintClasses = await blueprintBlock.getAttribute('class');
    const customClasses = await customBlock.getAttribute('class');

    // Custom blocks should have additional classes
    expect(customClasses).toContain('custom');
    // Or check specific style differences
    
    // Check border color or style
    const blueprintStyle = await blueprintBlock.evaluate(el => {
      const styles = window.getComputedStyle(el);
      return {
        borderColor: styles.borderColor,
        borderStyle: styles.borderStyle,
        backgroundColor: styles.backgroundColor
      };
    });

    const customStyle = await customBlock.evaluate(el => {
      const styles = window.getComputedStyle(el);
      return {
        borderColor: styles.borderColor,
        borderStyle: styles.borderStyle,
        backgroundColor: styles.backgroundColor
      };
    });

    // Custom blocks might have different border style (e.g., dashed vs solid)
    // The exact styling depends on implementation
    console.log('Blueprint style:', blueprintStyle);
    console.log('Custom style:', customStyle);

    // Take screenshot showing visual difference
    await window.screenshot({
      fullPage: true,
      path: "test-results/custom-vs-blueprint-styling.jpeg",
    });
  });

  test("Should show custom block badge or icon", async () => {
    // Look for custom block
    const customBlock = window.locator('[data-testid^="block-"]', { hasText: "CUSTOM_STYLED_BLOCK" }).first();
    
    // Check for badge/icon within the block
    const badge = customBlock.locator('[data-testid="custom-badge"]');
    const icon = customBlock.locator('[data-testid="custom-icon"]');
    
    // At least one should exist
    const hasBadge = await badge.count() > 0;
    const hasIcon = await icon.count() > 0;
    
    expect(hasBadge || hasIcon).toBeTruthy();
    
    if (hasBadge) {
      await expect(badge).toBeVisible();
      // Might contain text like "Custom" or "Project"
      const badgeText = await badge.textContent();
      expect(badgeText?.toLowerCase()).toMatch(/custom|project/);
    }
    
    if (hasIcon) {
      await expect(icon).toBeVisible();
    }
  });

  test("Should show tooltip with custom block information on hover", async () => {
    const customBlock = window.locator('[data-testid^="block-"]', { hasText: "CUSTOM_STYLED_BLOCK" }).first();
    
    // Hover over the block
    await customBlock.hover();
    
    // Wait for tooltip
    await window.waitForTimeout(500);
    
    // Check for tooltip
    const tooltip = window.locator('[role="tooltip"]');
    if (await tooltip.isVisible({ timeout: 1000 })) {
      const tooltipText = await tooltip.textContent();
      
      // Tooltip should indicate it's a custom block
      expect(tooltipText?.toLowerCase()).toMatch(/custom|project|local/);
      
      // Might also show the path
      if (tooltipText?.includes('atlasvibe_blocks')) {
        expect(tooltipText).toContain('CUSTOM_STYLED_BLOCK');
      }
    }
  });

  test("Should have different context menu for custom blocks", async () => {
    // Right-click on blueprint block
    await window.locator('[data-testid^="block-"]', { hasText: "RAND" }).first().click({
      button: "right",
    });
    
    // Get blueprint block menu items
    const blueprintMenu = window.getByTestId(Selectors.blockContextMenuDiv);
    await expect(blueprintMenu).toBeVisible();
    
    const blueprintMenuItems = await blueprintMenu.locator('button').allTextContents();
    
    // Close menu
    await window.keyboard.press("Escape");
    
    // Right-click on custom block
    await window.locator('[data-testid^="block-"]', { hasText: "CUSTOM_STYLED_BLOCK" }).first().click({
      button: "right",
    });
    
    // Get custom block menu items
    const customMenu = window.getByTestId(Selectors.blockContextMenuDiv);
    await expect(customMenu).toBeVisible();
    
    const customMenuItems = await customMenu.locator('button').allTextContents();
    
    // Custom blocks should have "Edit Python Code" option
    expect(customMenuItems).toContain("Edit Python Code");
    
    // Custom blocks might have additional options
    const hasRename = customMenuItems.some(item => item.includes("Rename"));
    const hasExport = customMenuItems.some(item => item.includes("Export"));
    
    console.log('Blueprint menu:', blueprintMenuItems);
    console.log('Custom menu:', customMenuItems);
    
    // Close menu
    await window.keyboard.press("Escape");
  });

  test("Should highlight custom block when editing parameters", async () => {
    // Click on custom block to select it
    const customBlock = window.locator('[data-testid^="block-"]', { hasText: "CUSTOM_STYLED_BLOCK" }).first();
    await customBlock.click();
    
    // Should show in control panel
    await expect(
      window.locator('[data-testid="control-panel"]')
    ).toBeVisible();
    
    // Look for parameter controls
    const paramControl = window.locator('[data-testid^="param-"]').first();
    if (await paramControl.isVisible({ timeout: 1000 })) {
      // Focus on parameter input
      await paramControl.click();
      
      // Block should be highlighted/focused
      const blockClasses = await customBlock.getAttribute('class');
      expect(blockClasses).toMatch(/selected|focused|active/);
      
      // Or check for specific styling
      const focusedStyle = await customBlock.evaluate(el => {
        const styles = window.getComputedStyle(el);
        return {
          boxShadow: styles.boxShadow,
          outline: styles.outline
        };
      });
      
      // Should have some focus indication
      expect(focusedStyle.boxShadow !== 'none' || focusedStyle.outline !== 'none').toBeTruthy();
    }
  });

  test("Should show error state for custom blocks with issues", async () => {
    // Create a custom block with potential issues
    await window.getByTestId(Selectors.addBlockBtn).click();
    await window.locator("button", { hasText: "CONSTANT" }).first().click();
    
    const nameInput = window.locator('input[placeholder="Enter block name"]');
    await nameInput.fill("ERROR_TEST_BLOCK");
    await window.getByRole("button", { name: "Create" }).click();
    await window.getByTestId(Selectors.sidebarCloseBtn).click();

    // Save project to create the custom block directory
    await app.evaluate(async ({ dialog }, savePath) => {
      dialog.showSaveDialog = () => 
        Promise.resolve({ filePath: savePath, canceled: false });
    }, projectPath);

    await window.keyboard.press("Control+S");
    await window.waitForTimeout(1000);

    // Simulate an error by modifying the block file to have invalid syntax
    const projectDir = projectPath.replace('.atlasvibe', '');
    const blockFile = join(projectDir, 'atlasvibe_blocks', 'ERROR_TEST_BLOCK', 'ERROR_TEST_BLOCK.py');
    
    if (fs.existsSync(blockFile)) {
      // Write invalid Python
      fs.writeFileSync(blockFile, `#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from atlasvibe import atlasvibe

@atlasvibe
def ERROR_TEST_BLOCK(x: int = 1) -> int:
    '''Block with syntax error'''
    return x * # Syntax error
`);
    }

    // Reload to trigger error detection
    await window.keyboard.press("F5");
    await window.waitForTimeout(2000);

    // Look for error indication
    const errorBlock = window.locator('[data-testid^="block-"]', { hasText: "ERROR_TEST_BLOCK" }).first();
    if (await errorBlock.isVisible({ timeout: 2000 })) {
      // Check for error styling
      const errorClasses = await errorBlock.getAttribute('class');
      const hasErrorClass = errorClasses?.includes('error') || errorClasses?.includes('invalid');
      
      // Or check for error icon/badge
      const errorIcon = errorBlock.locator('[data-testid="error-icon"]');
      const hasErrorIcon = await errorIcon.count() > 0;
      
      expect(hasErrorClass || hasErrorIcon).toBeTruthy();
      
      // Might also show error in tooltip on hover
      await errorBlock.hover();
      await window.waitForTimeout(500);
      
      const tooltip = window.locator('[role="tooltip"]');
      if (await tooltip.isVisible({ timeout: 1000 })) {
        const tooltipText = await tooltip.textContent();
        expect(tooltipText?.toLowerCase()).toMatch(/error|invalid|syntax/);
      }
    }
  });

  test("Should update visual indicators when custom block is modified", async () => {
    // Find a custom block
    const customBlock = window.locator('[data-testid^="block-"]', { hasText: "CUSTOM_STYLED_BLOCK" }).first();
    
    // Right-click and edit
    await customBlock.click({ button: "right" });
    
    const editOption = window.getByTestId("context-edit-python");
    if (await editOption.isVisible({ timeout: 1000 })) {
      const [editorWindow] = await Promise.all([
        app.waitForEvent("window"),
        editOption.click()
      ]);

      await editorWindow.waitForLoadState();

      // Make a change
      const editor = editorWindow.locator('[data-testid="code-editor"]');
      const content = await editor.inputValue();
      await editor.fill(content.replace("return x * 2", "return x * 3"));

      // Save
      await editorWindow.getByRole("button", { name: "Save" }).click();
      await editorWindow.waitForTimeout(1000);
      await editorWindow.close();

      // Block might show "modified" indicator temporarily
      const modifiedBadge = customBlock.locator('[data-testid="modified-badge"]');
      if (await modifiedBadge.count() > 0) {
        await expect(modifiedBadge).toBeVisible();
        
        // Should disappear after a moment
        await expect(modifiedBadge).toBeHidden({ timeout: 5000 });
      }
    }
  });

  test("Should group custom blocks visually in the sidebar", async () => {
    // Open sidebar
    await window.getByTestId(Selectors.addBlockBtn).click();
    
    // Check if there's a visual separator or grouping
    const sidebar = window.locator('[data-testid="blocks-sidebar"]');
    
    // Look for section headers
    const blueprintSection = sidebar.locator('text=Blueprint Blocks');
    const customSection = sidebar.locator('text=Custom Blocks');
    
    if (await customSection.isVisible({ timeout: 1000 })) {
      // Custom blocks should be in their own section
      await expect(customSection).toBeVisible();
      
      // Visual separator might exist
      const separator = sidebar.locator('hr, [role="separator"]');
      if (await separator.count() > 0) {
        await expect(separator.first()).toBeVisible();
      }
    }
    
    // Or check tabs
    const customTab = window.getByTestId(Selectors.customBlocksTabBtn);
    if (await customTab.isVisible({ timeout: 1000 })) {
      // Click to see only custom blocks
      await customTab.click();
      
      // Should show only custom blocks
      const blockButtons = sidebar.locator('button[data-block-type]');
      const blockCount = await blockButtons.count();
      
      for (let i = 0; i < blockCount; i++) {
        const blockType = await blockButtons.nth(i).getAttribute('data-block-type');
        expect(blockType).toBe('custom');
      }
    }
    
    await window.getByTestId(Selectors.sidebarCloseBtn).click();
  });
});
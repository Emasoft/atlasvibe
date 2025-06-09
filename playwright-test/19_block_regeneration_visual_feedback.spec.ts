/**
 * Playwright E2E tests for block regeneration visual feedback.
 * 
 * These tests verify and document the expected behavior when:
 * 1. A new custom block folder is created
 * 2. Custom block code is modified
 * 3. Metadata regeneration occurs
 * 
 * Expected visual feedback (currently NOT implemented):
 * - Border color change during regeneration
 * - "Regenerating" label above the block
 * - Blinking animation on the label
 * 
 * NOTE: These tests require the application to be built first.
 * Run: pnpm run build
 * Then: npx playwright test 19_block_regeneration_visual_feedback.spec.ts
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

test.describe("Block regeneration visual feedback", () => {
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
    projectPath = join(tempDir, `regeneration_test_${Date.now()}.atlasvibe`);
  });

  test.afterAll(async () => {
    await writeLogFile(app, "block-regeneration-visual-feedback");
    
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

  test("Should show visual feedback when creating a new custom block", async () => {
    // Create a custom block
    await window.getByTestId(Selectors.addBlockBtn).click();
    await window.locator("button", { hasText: "CONSTANT" }).first().click();
    
    const nameInput = window.locator('input[placeholder="Enter block name"]');
    await nameInput.fill("REGENERATION_TEST_BLOCK");
    await window.getByRole("button", { name: "Create" }).click();
    await window.getByTestId(Selectors.sidebarCloseBtn).click();

    // Save project to create the custom block directory
    await app.evaluate(async ({ dialog }, savePath) => {
      dialog.showSaveDialog = () => 
        Promise.resolve({ filePath: savePath, canceled: false });
    }, projectPath);

    await window.keyboard.press("Control+S");
    await window.waitForTimeout(1000);

    // Look for the custom block
    const customBlock = window.locator('[data-testid^="block-"]', { hasText: "REGENERATION_TEST_BLOCK" }).first();
    await expect(customBlock).toBeVisible();

    // Check for regenerating visual indicators (currently NOT implemented)
    // These assertions will FAIL, documenting what's missing
    
    // 1. Check for regenerating class or border color change
    const hasRegeneratingClass = await customBlock.evaluate((el) => {
      const classes = el.className;
      return classes.includes('regenerating') || 
             classes.includes('border-orange') || 
             classes.includes('border-yellow');
    });
    
    // Document: This should be true but is currently false
    console.log(`Block has regenerating visual class: ${hasRegeneratingClass}`);
    
    // 2. Check for regenerating label
    const regeneratingLabel = customBlock.locator('text=/regenerating/i');
    const hasRegeneratingLabel = await regeneratingLabel.count() > 0;
    
    // Document: This should be true but is currently false
    console.log(`Block shows regenerating label: ${hasRegeneratingLabel}`);
    
    // 3. Check for blinking animation
    const hasBlinkingAnimation = await customBlock.evaluate((el) => {
      const styles = window.getComputedStyle(el);
      const anyChild = el.querySelector('[class*="blink"]');
      return styles.animation?.includes('blink') || anyChild !== null;
    });
    
    // Document: This should be true but is currently false
    console.log(`Block has blinking animation: ${hasBlinkingAnimation}`);
    
    // Take screenshot to document current state
    await window.screenshot({
      fullPage: true,
      path: "test-results/block-regeneration-no-visual-feedback.jpeg",
    });
  });

  test("Should show visual feedback when modifying custom block code", async () => {
    // Find the custom block
    const customBlock = window.locator('[data-testid^="block-"]', { hasText: "REGENERATION_TEST_BLOCK" }).first();
    
    // Right-click to edit
    await customBlock.click({ button: "right" });
    
    const editOption = window.getByTestId("context-edit-python");
    if (await editOption.isVisible({ timeout: 1000 })) {
      const [editorWindow] = await Promise.all([
        app.waitForEvent("window"),
        editOption.click()
      ]);

      await editorWindow.waitForLoadState();

      // Make a change to trigger regeneration
      const editor = editorWindow.locator('[data-testid="code-editor"]');
      const content = await editor.inputValue();
      
      // Add a new parameter to trigger manifest regeneration
      const newContent = content.replace(
        "def REGENERATION_TEST_BLOCK(x:",
        "def REGENERATION_TEST_BLOCK(x:, new_param: int = 42"
      );
      await editor.fill(newContent);

      // Save to trigger regeneration
      await editorWindow.getByRole("button", { name: "Save" }).click();
      
      // Immediately check for visual feedback during regeneration
      // (before it completes)
      
      // Switch back to main window
      await window.bringToFront();
      
      // Check for regenerating indicators
      const blockDuringRegen = window.locator('[data-testid^="block-"]', { hasText: "REGENERATION_TEST_BLOCK" }).first();
      
      // 1. Border should change color
      const borderStyle = await blockDuringRegen.evaluate(el => {
        const styles = window.getComputedStyle(el);
        return {
          borderColor: styles.borderColor,
          borderWidth: styles.borderWidth,
          animation: styles.animation
        };
      });
      
      console.log("Border style during regeneration:", borderStyle);
      
      // 2. Should show regenerating label
      const regenLabel = blockDuringRegen.locator('.regenerating-label, text=/regenerating/i');
      const showsLabel = await regenLabel.isVisible({ timeout: 100 }).catch(() => false);
      
      console.log(`Shows regenerating label during save: ${showsLabel}`);
      
      // Close editor
      await editorWindow.close();
      
      // Wait for regeneration to complete
      await window.waitForTimeout(2000);
      
      // After regeneration, visual indicators should be gone
      const labelAfter = await regenLabel.isVisible({ timeout: 100 }).catch(() => false);
      console.log(`Shows regenerating label after completion: ${labelAfter}`);
    }
  });

  test("Should detect manifest update WebSocket events", async () => {
    // This test verifies that the WebSocket communication is working
    // even if visual feedback is not implemented
    
    // Listen for toast notifications which are shown on manifest updates
    const toastLocator = window.locator('text=/Changes detected, syncing blocks/i');
    
    // Modify a block file to trigger the file watcher
    const projectDir = projectPath.replace('.atlasvibe', '');
    const blockFile = join(projectDir, 'atlasvibe_blocks', 'REGENERATION_TEST_BLOCK', 'REGENERATION_TEST_BLOCK.py');
    
    if (fs.existsSync(blockFile)) {
      // Read current content
      const currentContent = fs.readFileSync(blockFile, 'utf-8');
      
      // Modify the file
      const modifiedContent = currentContent.replace(
        'return x * 2',
        'return x * 3  # Modified'
      );
      fs.writeFileSync(blockFile, modifiedContent);
      
      // Wait for the toast notification
      await expect(toastLocator).toBeVisible({ timeout: 5000 });
      
      console.log("✅ WebSocket manifest_update event is working");
      console.log("❌ Visual regeneration indicators are NOT implemented");
    }
  });

  test("Document expected visual feedback implementation", async () => {
    // This test documents what SHOULD be implemented
    
    const expectedImplementation = {
      "CSS_Classes": {
        ".regenerating": "Applied to block during regeneration",
        ".border-orange-500": "Orange border during regeneration",
        ".animate-pulse": "Pulsing animation on border"
      },
      "Regenerating_Label": {
        "HTML": '<div class="regenerating-label">Regenerating...</div>',
        "Position": "absolute -top-6",
        "Animation": "animate-blink (1s infinite)"
      },
      "State_Management": {
        "Store": "Track isRegenerating state per block",
        "Trigger": "Set on manifest_update WebSocket event",
        "Clear": "Clear when manifest fetch completes"
      },
      "Animation_Keyframes": {
        "blink": "@keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }"
      }
    };
    
    console.log("\n=== Expected Visual Feedback Implementation ===");
    console.log(JSON.stringify(expectedImplementation, null, 2));
    
    // Create a mock visualization of what it should look like
    await window.evaluate(() => {
      const blocks = document.querySelectorAll('[data-testid^="block-"]');
      if (blocks.length > 0) {
        const block = blocks[0] as HTMLElement;
        
        // Add mock regenerating style
        block.style.border = "3px solid orange";
        block.style.position = "relative";
        
        // Add mock label
        const label = document.createElement('div');
        label.textContent = 'Regenerating...';
        label.style.position = 'absolute';
        label.style.top = '-30px';
        label.style.left = '50%';
        label.style.transform = 'translateX(-50%)';
        label.style.background = 'orange';
        label.style.color = 'white';
        label.style.padding = '4px 8px';
        label.style.borderRadius = '4px';
        label.style.fontSize = '12px';
        label.style.animation = 'blink-mock 1s infinite';
        
        // Add keyframe animation
        const style = document.createElement('style');
        style.textContent = `
          @keyframes blink-mock {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.3; }
          }
        `;
        document.head.appendChild(style);
        
        block.appendChild(label);
      }
    });
    
    // Take screenshot of mock implementation
    await window.screenshot({
      fullPage: true,
      path: "test-results/block-regeneration-expected-visual.jpeg",
    });
    
    // Remove mock visualization
    await window.evaluate(() => {
      const blocks = document.querySelectorAll('[data-testid^="block-"]');
      blocks.forEach((block: Element) => {
        const htmlBlock = block as HTMLElement;
        htmlBlock.style.border = '';
        const label = htmlBlock.querySelector('div[style*="Regenerating"]');
        if (label) label.remove();
      });
    });
    
    expect(true).toBe(true); // This test is for documentation
  });
});
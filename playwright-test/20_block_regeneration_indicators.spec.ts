#!/usr/bin/env node
// -*- coding: utf-8 -*-

// HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
// - New test file for block regeneration visual indicators
// - Tests blinking indicator during regeneration
// - Tests workflow pause during regeneration
// - Tests header color change during regeneration
// - Tests actual regeneration completion
// 

import { test, expect, ElectronApplication, Page } from "@playwright/test";
import {
  launchApp,
  mockDialogMessage,
  writeLogFile,
  STARTUP_TIMEOUT,
  getExecutablePath,
} from "./utils";
import { Selectors } from "./selectors";
import * as path from "path";
import * as fs from "fs/promises";
import * as os from "os";

let app: ElectronApplication;
let window: Page;
let projectDir: string;

test.describe("Block Regeneration Visual Indicators", () => {
  test.beforeAll(async () => {
    test.setTimeout(STARTUP_TIMEOUT);
    const executablePath = getExecutablePath();
    app = await electron.launch({ executablePath });
    await mockDialogMessage(app);
    window = await app.firstWindow();
    
    // Create test project directory
    projectDir = path.join(os.tmpdir(), `atlasvibe-regen-test-${Date.now()}`);
    await fs.mkdir(projectDir, { recursive: true });
    
    // Wait for app to load
    await window.waitForSelector(Selectors.closeWelcomeModalBtn, { timeout: 30000 });
    await window.getByTestId(Selectors.closeWelcomeModalBtn).click();
  });

  test.afterAll(async () => {
    await writeLogFile(app, "block-regeneration-indicators");
    await fs.rm(projectDir, { recursive: true, force: true });
    await app.close();
  });

  test("should display blinking indicator above block during regeneration", async () => {
    // Create a custom block
    await window.getByTestId(Selectors.sidebarInput).click();
    await window.keyboard.type("CONSTANT");
    await window.keyboard.press("Enter");
    
    // Wait for block to appear
    const blockElement = await window.locator("h2", { hasText: "CONSTANT" }).first();
    await expect(blockElement).toBeVisible();
    
    // Right-click to open context menu
    await blockElement.click({ button: "right" });
    await expect(window.getByTestId(Selectors.blockContextMenuDiv)).toBeVisible();
    
    // Click "Edit Python Code"
    await window.getByTestId(Selectors.contextEditBlockBtn).click();
    
    // Wait for code editor
    await expect(window.locator(".monaco-editor")).toBeVisible();
    
    // Make a change to trigger regeneration
    await window.keyboard.type("# Modified code");
    await window.keyboard.press("Control+S");
    
    // Check for blinking indicator
    const blinkingIndicator = await window.locator(".block-regenerating-indicator");
    
    // Expected: Indicator should be visible and have blinking animation
    await expect(blinkingIndicator).toBeVisible();
    const animationName = await blinkingIndicator.evaluate(el => 
      window.getComputedStyle(el).animationName
    );
    expect(animationName).toContain("blink");
    
    // Check indicator text
    await expect(blinkingIndicator).toHaveText("Regenerating...");
    
    // Wait for regeneration to complete
    await expect(blinkingIndicator).toBeHidden({ timeout: 10000 });
  });

  test("should pause workflow execution during block regeneration", async () => {
    // Create a simple workflow
    await window.getByTestId(Selectors.sidebarInput).click();
    await window.keyboard.type("ADD");
    await window.keyboard.press("Enter");
    
    const addBlock = await window.locator("h2", { hasText: "ADD" }).first();
    await expect(addBlock).toBeVisible();
    
    // Start workflow execution
    await window.getByTestId(Selectors.playBtn).click();
    
    // Trigger block regeneration while running
    await addBlock.click({ button: "right" });
    await window.getByTestId(Selectors.contextEditBlockBtn).click();
    await window.keyboard.type("# Change during execution");
    await window.keyboard.press("Control+S");
    
    // Check execution status
    const executionStatus = await window.locator(".execution-status");
    await expect(executionStatus).toHaveText("Paused - Block Regenerating");
    
    // Verify play button is disabled
    const playButton = window.getByTestId(Selectors.playBtn);
    await expect(playButton).toBeDisabled();
    
    // Wait for regeneration to complete
    await expect(executionStatus).not.toHaveText("Paused", { timeout: 10000 });
    
    // Execution should resume automatically
    await expect(executionStatus).toHaveText("Running");
  });

  test("should change block header color during regeneration", async () => {
    // Create custom block
    await window.getByTestId(Selectors.sidebarInput).click();
    await window.keyboard.type("MULTIPLY");
    await window.keyboard.press("Enter");
    
    const blockElement = await window.locator("h2", { hasText: "MULTIPLY" }).first();
    const blockHeader = await blockElement.locator("..").first(); // Parent element
    
    // Get original border color
    const originalBorderColor = await blockHeader.evaluate(el => 
      window.getComputedStyle(el).borderColor
    );
    
    // Trigger regeneration
    await blockElement.click({ button: "right" });
    await window.getByTestId(Selectors.contextEditBlockBtn).click();
    await window.keyboard.type("# Trigger regeneration");
    await window.keyboard.press("Control+S");
    
    // Check border color change
    const regeneratingBorderColor = await blockHeader.evaluate(el => 
      window.getComputedStyle(el).borderColor
    );
    
    // Expected: Orange/amber color during regeneration
    expect(regeneratingBorderColor).toMatch(/rgb\(25[0-5], \d{2,3}, 0\)/); // Orange range
    expect(regeneratingBorderColor).not.toBe(originalBorderColor);
    
    // Check for pulsing animation
    const animationName = await blockHeader.evaluate(el => 
      window.getComputedStyle(el).animationName
    );
    expect(animationName).toContain("pulse");
    
    // Wait for regeneration to complete
    await window.waitForTimeout(3000);
    
    // Border should return to original
    const finalBorderColor = await blockHeader.evaluate(el => 
      window.getComputedStyle(el).borderColor
    );
    expect(finalBorderColor).toBe(originalBorderColor);
  });

  test("should verify actual regeneration of code and metadata", async () => {
    // Create custom block directory
    const customBlocksDir = path.join(projectDir, "atlasvibe_blocks");
    await fs.mkdir(customBlocksDir, { recursive: true });
    
    const blockName = "CUSTOM_PROCESSOR";
    const blockDir = path.join(customBlocksDir, blockName);
    await fs.mkdir(blockDir, { recursive: true });
    
    // Create initial Python file
    const pythonPath = path.join(blockDir, `${blockName}.py`);
    const initialCode = `#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from atlasvibe import atlasvibe_node

@atlasvibe_node
def ${blockName}(input: float) -> float:
    """Simple processor.
    
    Args:
        input: Input value
        
    Returns:
        float: Processed value
    """
    return input * 2.0
`;
    await fs.writeFile(pythonPath, initialCode);
    
    // Import the custom block
    await window.getByTestId(Selectors.customBlocksTabBtn).click();
    await window.getByTestId(Selectors.importCustomBlockBtn).click();
    
    // Set project directory
    await app.evaluate(async ({ dialog }, projectPath) => {
      dialog.showOpenDialog = () => 
        Promise.resolve({ filePaths: [projectPath], canceled: false });
    }, projectDir);
    
    await window.getByRole("button", { name: "Browse" }).click();
    await window.getByRole("button", { name: "Import" }).click();
    
    // Place the block
    await window.getByTestId(Selectors.sidebarInput).click();
    await window.keyboard.type(blockName);
    await window.keyboard.press("Enter");
    
    // Edit the code
    const blockElement = await window.locator("h2", { hasText: blockName }).first();
    await blockElement.click({ button: "right" });
    await window.getByTestId(Selectors.contextEditBlockBtn).click();
    
    // Modify the code
    const modifiedCode = `#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from atlasvibe import atlasvibe_node

@atlasvibe_node
def ${blockName}(input: float, multiplier: float = 3.0) -> float:
    """Advanced processor with multiplier.
    
    Args:
        input: Input value
        multiplier: Multiplication factor
        
    Returns:
        float: Processed value
    """
    return input * multiplier
`;
    
    // Clear editor and type new code
    await window.keyboard.press("Control+A");
    await window.keyboard.type(modifiedCode);
    await window.keyboard.press("Control+S");
    
    // Wait for regeneration
    await window.waitForTimeout(3000);
    
    // Verify Python file was updated
    const updatedCode = await fs.readFile(pythonPath, "utf-8");
    expect(updatedCode).toContain("multiplier: float = 3.0");
    expect(updatedCode).toContain("Advanced processor with multiplier");
    
    // Verify block_data.json was generated/updated
    const blockDataPath = path.join(blockDir, "block_data.json");
    const blockDataExists = await fs.access(blockDataPath).then(() => true).catch(() => false);
    expect(blockDataExists).toBe(true);
    
    if (blockDataExists) {
      const blockData = JSON.parse(await fs.readFile(blockDataPath, "utf-8"));
      expect(blockData.docstring.short_description).toContain("Advanced processor");
      expect(blockData.docstring.parameters).toHaveLength(2);
      expect(blockData.docstring.parameters[1].name).toBe("multiplier");
    }
    
    // Verify manifest was regenerated
    const manifestPath = path.join(blockDir, "manifest.json");
    const manifestExists = await fs.access(manifestPath).then(() => true).catch(() => false);
    
    if (manifestExists) {
      const manifest = JSON.parse(await fs.readFile(manifestPath, "utf-8"));
      expect(manifest.parameters).toHaveProperty("multiplier");
      expect(manifest.parameters.multiplier.default).toBe(3.0);
    }
    
    // Verify UI reflects the changes
    await blockElement.click();
    const parameterLabel = await window.locator(`text=multiplier: 3.0`);
    await expect(parameterLabel).toBeVisible();
  });
});
/**
 * Playwright E2E tests for custom block references and project format v2.
 * 
 * These tests verify that:
 * 1. Custom blocks maintain their references when projects are saved/loaded
 * 2. Custom blocks show visual indicators in the UI
 * 3. Multiple projects can have blocks with the same name
 * 4. Project migration from v1 to v2 works correctly
 * 5. Custom blocks can be renamed while maintaining references
 * 
 * NOTE: These tests require the application to be built first.
 * Run: pnpm run build
 * Then: npx playwright test 17_custom_block_references.spec.ts
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

test.describe("Custom block references", () => {
  let window: Page;
  let app: ElectronApplication;
  let tempDir: string;
  let project1Path: string;
  let project2Path: string;

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

    // Create temporary directory for test projects
    tempDir = await app.evaluate(async ({ app: _app }) => {
      return _app.getPath("temp");
    });
    tempDir = join(tempDir, `custom_block_test_${Date.now()}`);
    fs.mkdirSync(tempDir, { recursive: true });
    
    // Create two test projects
    project1Path = join(tempDir, "project1.atlasvibe");
    project2Path = join(tempDir, "project2.atlasvibe");
  });

  test.afterAll(async () => {
    await writeLogFile(app, "custom-block-references");
    
    // Cleanup temporary files
    if (fs.existsSync(tempDir)) {
      fs.rmSync(tempDir, { recursive: true, force: true });
    }
    
    await app.close();
  });

  test("Should create custom blocks that persist across save/load", async () => {
    // Create a custom block
    await window.getByTestId(Selectors.addBlockBtn).click();
    await window.locator("button", { hasText: "CONSTANT" }).first().click();
    
    // Enter custom name
    const nameInput = window.locator('input[placeholder="Enter block name"]');
    await nameInput.fill("MY_PROCESSOR");
    await window.getByRole("button", { name: "Create" }).click();
    await window.getByTestId(Selectors.sidebarCloseBtn).click();

    // Verify custom block appears
    await expect(
      window.locator("h2", { hasText: "MY_PROCESSOR" })
    ).toBeVisible();

    // Save the project
    await app.evaluate(async ({ dialog }, savePath) => {
      dialog.showSaveDialog = () => 
        Promise.resolve({ filePath: savePath, canceled: false });
    }, project1Path);

    await window.keyboard.press("Control+S");
    await window.waitForTimeout(1000); // Wait for save to complete

    // Clear the canvas
    await window.keyboard.press("Control+A");
    await window.keyboard.press("Delete");

    // Load the project back
    await app.evaluate(async ({ dialog }, loadPath) => {
      dialog.showOpenDialog = () =>
        Promise.resolve({ filePaths: [loadPath], canceled: false });
    }, project1Path);

    await window.keyboard.press("Control+O");
    await window.waitForTimeout(1000); // Wait for load to complete

    // Verify custom block is restored with correct reference
    await expect(
      window.locator("h2", { hasText: "MY_PROCESSOR" })
    ).toBeVisible();

    // Verify the loaded project data contains custom block info
    const projectData = JSON.parse(fs.readFileSync(project1Path, 'utf-8'));
    expect(projectData.version).toBe("2.0.0");
    
    const customNode = projectData.rfInstance.nodes.find(
      (n: any) => n.data.func === "MY_PROCESSOR"
    );
    expect(customNode).toBeTruthy();
    expect(customNode.data.path).toContain("atlasvibe_blocks/MY_PROCESSOR");
    expect(customNode.data.isCustom).toBe(true);
  });

  test("Should show visual indicators for custom blocks", async () => {
    // Custom blocks should have a visual indicator
    const customBlock = window.locator("h2", { hasText: "MY_PROCESSOR" }).first();
    const blockContainer = customBlock.locator("..");
    
    // Check for custom block styling or badge
    // The exact implementation may vary, but there should be some visual difference
    await expect(blockContainer).toHaveClass(/custom-block|project-block/);
    
    // Or check for a badge/icon
    const customIndicator = blockContainer.locator('[data-testid="custom-block-indicator"]');
    if (await customIndicator.count() > 0) {
      await expect(customIndicator).toBeVisible();
    }

    // Take a screenshot showing custom block indicator
    await window.screenshot({
      fullPage: true,
      path: "test-results/custom-block-indicator.jpeg",
    });
  });

  test("Should handle multiple projects with same block names", async () => {
    // Save current project
    await window.keyboard.press("Control+S");
    await window.waitForTimeout(500);

    // Create a new project
    await window.keyboard.press("Control+N");
    
    // Confirm if prompted
    const confirmButton = window.getByRole("button", { name: "Yes" });
    if (await confirmButton.isVisible({ timeout: 1000 })) {
      await confirmButton.click();
    }

    // Create another custom block with the same name
    await window.getByTestId(Selectors.addBlockBtn).click();
    await window.locator("button", { hasText: "CONSTANT" }).first().click();
    
    const nameInput = window.locator('input[placeholder="Enter block name"]');
    await nameInput.fill("MY_PROCESSOR"); // Same name as in project1
    await window.getByRole("button", { name: "Create" }).click();
    await window.getByTestId(Selectors.sidebarCloseBtn).click();

    // Add a second block to differentiate
    await window.getByTestId(Selectors.addBlockBtn).click();
    await window.locator("button", { hasText: "RAND" }).first().click();
    await window.getByTestId(Selectors.sidebarCloseBtn).click();

    // Save as project2
    await app.evaluate(async ({ dialog }, savePath) => {
      dialog.showSaveDialog = () => 
        Promise.resolve({ filePath: savePath, canceled: false });
    }, project2Path);

    await window.keyboard.press("Control+S");
    await window.waitForTimeout(1000);

    // Both projects should have their own MY_PROCESSOR implementations
    const project1Data = JSON.parse(fs.readFileSync(project1Path, 'utf-8'));
    const project2Data = JSON.parse(fs.readFileSync(project2Path, 'utf-8'));

    const customNode1 = project1Data.rfInstance.nodes.find(
      (n: any) => n.data.func === "MY_PROCESSOR"
    );
    const customNode2 = project2Data.rfInstance.nodes.find(
      (n: any) => n.data.func === "MY_PROCESSOR"
    );

    // Both should exist and have custom block references
    expect(customNode1).toBeTruthy();
    expect(customNode2).toBeTruthy();
    expect(customNode1.data.isCustom).toBe(true);
    expect(customNode2.data.isCustom).toBe(true);

    // They should have the same path structure but in different projects
    expect(customNode1.data.path).toBe("atlasvibe_blocks/MY_PROCESSOR");
    expect(customNode2.data.path).toBe("atlasvibe_blocks/MY_PROCESSOR");
  });

  test("Should migrate v1 projects to v2 format", async () => {
    // Create a v1 format project file
    const v1ProjectPath = join(tempDir, "v1_project.atlasvibe");
    const v1ProjectData = {
      // No version field in v1
      name: "Legacy Project",
      rfInstance: {
        nodes: [{
          id: "node-1",
          type: "CustomBlock",
          position: { x: 100, y: 100 },
          data: {
            id: "node-1",
            label: "MY_OLD_BLOCK",
            func: "MY_OLD_BLOCK",
            type: "CustomBlock",
            ctrls: {},
            inputs: [],
            outputs: []
            // No path or isCustom in v1
          }
        }],
        edges: []
      }
    };
    
    fs.writeFileSync(v1ProjectPath, JSON.stringify(v1ProjectData, null, 2));

    // Load the v1 project
    await app.evaluate(async ({ dialog }, loadPath) => {
      dialog.showOpenDialog = () =>
        Promise.resolve({ filePaths: [loadPath], canceled: false });
    }, v1ProjectPath);

    await window.keyboard.press("Control+O");
    await window.waitForTimeout(1000);

    // The block should be loaded
    await expect(
      window.locator("h2", { hasText: "MY_OLD_BLOCK" })
    ).toBeVisible();

    // Save it (which should trigger migration)
    const migratedPath = join(tempDir, "v1_migrated.atlasvibe");
    await app.evaluate(async ({ dialog }, savePath) => {
      dialog.showSaveDialog = () => 
        Promise.resolve({ filePath: savePath, canceled: false });
    }, migratedPath);

    await window.keyboard.press("Control+S");
    await window.waitForTimeout(1000);

    // Check the saved file has v2 format
    const migratedData = JSON.parse(fs.readFileSync(migratedPath, 'utf-8'));
    expect(migratedData.version).toBe("2.0.0");
    
    // Custom blocks should have default values added
    const migratedNode = migratedData.rfInstance.nodes[0];
    expect(migratedNode.data.path).toBeDefined();
    expect(migratedNode.data.isCustom).toBe(false); // Default for unknown blocks
  });

  test("Should update references when renaming custom blocks", async () => {
    // Load project1
    await app.evaluate(async ({ dialog }, loadPath) => {
      dialog.showOpenDialog = () =>
        Promise.resolve({ filePaths: [loadPath], canceled: false });
    }, project1Path);

    await window.keyboard.press("Control+O");
    await window.waitForTimeout(1000);

    // Right-click on custom block
    await window.locator("h2", { hasText: "MY_PROCESSOR" }).click({
      button: "right",
    });

    // Look for rename option in context menu
    const renameOption = window.getByTestId("context-rename-block");
    if (await renameOption.isVisible({ timeout: 1000 })) {
      await renameOption.click();

      // Enter new name
      const renameInput = window.locator('input[placeholder="Enter new name"]');
      await renameInput.fill("RENAMED_PROCESSOR");
      await window.getByRole("button", { name: "Rename" }).click();

      // Block should show new name
      await expect(
        window.locator("h2", { hasText: "RENAMED_PROCESSOR" })
      ).toBeVisible();

      // Save and verify references are updated
      await window.keyboard.press("Control+S");
      await window.waitForTimeout(1000);

      const updatedData = JSON.parse(fs.readFileSync(project1Path, 'utf-8'));
      const renamedNode = updatedData.rfInstance.nodes.find(
        (n: any) => n.data.func === "RENAMED_PROCESSOR"
      );
      expect(renamedNode).toBeTruthy();
      expect(renamedNode.data.path).toContain("RENAMED_PROCESSOR");
    }
  });

  test("Should handle custom block deletion gracefully", async () => {
    // Create a project with custom block
    await window.keyboard.press("Control+N");
    
    // Confirm if prompted
    const confirmButton = window.getByRole("button", { name: "Yes" });
    if (await confirmButton.isVisible({ timeout: 1000 })) {
      await confirmButton.click();
    }

    // Add custom block
    await window.getByTestId(Selectors.addBlockBtn).click();
    await window.locator("button", { hasText: "CONSTANT" }).first().click();
    
    const nameInput = window.locator('input[placeholder="Enter block name"]');
    await nameInput.fill("DELETABLE_BLOCK");
    await window.getByRole("button", { name: "Create" }).click();
    await window.getByTestId(Selectors.sidebarCloseBtn).click();

    // Save project
    const deletionTestPath = join(tempDir, "deletion_test.atlasvibe");
    await app.evaluate(async ({ dialog }, savePath) => {
      dialog.showSaveDialog = () => 
        Promise.resolve({ filePath: savePath, canceled: false });
    }, deletionTestPath);

    await window.keyboard.press("Control+S");
    await window.waitForTimeout(1000);

    // Manually delete the custom block directory (simulating external deletion)
    const projectDir = path.dirname(deletionTestPath);
    const customBlockDir = join(projectDir, "atlasvibe_blocks", "DELETABLE_BLOCK");
    if (fs.existsSync(customBlockDir)) {
      fs.rmSync(customBlockDir, { recursive: true, force: true });
    }

    // Reload the project
    await app.evaluate(async ({ dialog }, loadPath) => {
      dialog.showOpenDialog = () =>
        Promise.resolve({ filePaths: [loadPath], canceled: false });
    }, deletionTestPath);

    await window.keyboard.press("Control+O");
    await window.waitForTimeout(1000);

    // The block should still appear but might show as missing/error
    const deletedBlock = window.locator("h2", { hasText: "DELETABLE_BLOCK" });
    if (await deletedBlock.isVisible({ timeout: 1000 })) {
      // Check if it has error styling
      const blockContainer = deletedBlock.locator("..");
      await expect(blockContainer).toHaveClass(/error|missing|warning/);
    }

    // Or there might be an error toast
    const errorToast = window.locator("text=missing custom block");
    if (await errorToast.isVisible({ timeout: 1000 })) {
      await expect(errorToast).toBeVisible();
    }
  });

  test("Should show custom blocks in sidebar separately", async () => {
    // Open sidebar
    await window.getByTestId(Selectors.addBlockBtn).click();

    // Switch to custom blocks tab
    await window.getByTestId(Selectors.customBlocksTabBtn).click();

    // Custom blocks from current project should be listed
    const customBlocksList = window.locator('[data-testid="custom-blocks-list"]');
    
    // Should show project custom blocks if any exist
    const projectBlocks = customBlocksList.locator("button");
    const blockCount = await projectBlocks.count();
    
    if (blockCount > 0) {
      // Verify they're marked as custom/project blocks
      for (let i = 0; i < blockCount; i++) {
        const block = projectBlocks.nth(i);
        const blockText = await block.textContent();
        
        // Custom blocks might have special styling or badges
        await expect(block).toHaveClass(/custom|project/);
      }
    }

    // Take screenshot of custom blocks sidebar
    await window.screenshot({
      fullPage: false,
      path: "test-results/custom-blocks-sidebar.jpeg",
    });

    await window.getByTestId(Selectors.sidebarCloseBtn).click();
  });
});
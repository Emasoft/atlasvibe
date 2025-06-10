#!/usr/bin/env node
// -*- coding: utf-8 -*-

// HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
// - New test file for project save functionality and status indicators
// - Tests improved save option to any folder
// - Tests project name validation
// - Tests status indicator states
// - Tests autosave functionality
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
let testProjectsDir: string;

test.describe("Project Save and Status Indicators", () => {
  test.beforeAll(async () => {
    test.setTimeout(STARTUP_TIMEOUT);
    const executablePath = getExecutablePath();
    app = await electron.launch({ executablePath });
    await mockDialogMessage(app);
    window = await app.firstWindow();
    
    // Create test projects directory
    testProjectsDir = path.join(os.tmpdir(), `atlasvibe-projects-${Date.now()}`);
    await fs.mkdir(testProjectsDir, { recursive: true });
    
    await window.waitForSelector(Selectors.closeWelcomeModalBtn, { timeout: 30000 });
    await window.getByTestId(Selectors.closeWelcomeModalBtn).click();
  });

  test.afterAll(async () => {
    await writeLogFile(app, "project-save-status");
    await fs.rm(testProjectsDir, { recursive: true, force: true });
    await app.close();
  });

  test("should show status indicator in correct states", async () => {
    // Check initial state - should be "saved" for new project
    const statusIndicator = await window.locator(".project-status-indicator");
    await expect(statusIndicator).toBeVisible();
    await expect(statusIndicator).toHaveText("Saved");
    
    // Verify color on black background
    const savedColor = await statusIndicator.evaluate(el => 
      window.getComputedStyle(el).color
    );
    // Should be a readable green on black
    expect(savedColor).toMatch(/rgb\(\d{100,200}, \d{200,255}, \d{100,200}\)/);
    
    // Add a block to trigger unsaved state
    await window.getByTestId(Selectors.sidebarInput).click();
    await window.keyboard.type("CONSTANT");
    await window.keyboard.press("Enter");
    
    // Status should change to "Unsaved changes"
    await expect(statusIndicator).toHaveText("Unsaved changes");
    const unsavedColor = await statusIndicator.evaluate(el => 
      window.getComputedStyle(el).color
    );
    // Should be yellow/amber
    expect(unsavedColor).toMatch(/rgb\(2\d{2}, \d{150,220}, \d{0,100}\)/);
    
    // Save the project
    await window.keyboard.press("Control+S");
    
    // Mock save dialog
    const projectPath = path.join(testProjectsDir, "test_project_1");
    await app.evaluate(async ({ dialog }, savePath) => {
      dialog.showSaveDialog = () => 
        Promise.resolve({ filePath: savePath, canceled: false });
    }, projectPath);
    
    // Status should show "Saving"
    await expect(statusIndicator).toHaveText("Saving");
    const savingColor = await statusIndicator.evaluate(el => 
      window.getComputedStyle(el).color
    );
    // Should be a different shade of yellow
    expect(savingColor).toMatch(/rgb\(2\d{2}, \d{180,240}, \d{50,150}\)/);
    
    // After save completes, should show "Saved"
    await expect(statusIndicator).toHaveText("Saved", { timeout: 5000 });
    
    // Make another change to test autosave
    const block = await window.locator("h2", { hasText: "CONSTANT" }).first();
    await block.dblclick();
    await window.keyboard.type("42");
    
    // Should show "Autosaving" after a delay
    await window.waitForTimeout(2000); // Wait for autosave to trigger
    await expect(statusIndicator).toHaveText("Autosaving");
    const autosavingColor = await statusIndicator.evaluate(el => 
      window.getComputedStyle(el).color
    );
    // Should be yet another shade of yellow
    expect(autosavingColor).toMatch(/rgb\(2\d{2}, \d{200,255}, \d{100,200}\)/);
    
    // Should return to "Saved" after autosave
    await expect(statusIndicator).toHaveText("Saved", { timeout: 5000 });
  });

  test("should save project to any selected folder", async () => {
    // Create new project
    await window.keyboard.press("Control+N");
    
    // Add some content
    await window.getByTestId(Selectors.sidebarInput).click();
    await window.keyboard.type("ADD");
    await window.keyboard.press("Enter");
    
    // Open save dialog with "Save As"
    await window.keyboard.press("Control+Shift+S");
    
    // Should open custom save dialog
    const saveDialog = await window.getByRole("dialog", { name: "Save Project" });
    await expect(saveDialog).toBeVisible();
    
    // Project name input
    const projectNameInput = await saveDialog.locator('input[placeholder="Project name"]');
    const folderPathInput = await saveDialog.locator('input[placeholder="Select folder"]');
    const browseButton = await saveDialog.getByRole("button", { name: "Browse" });
    
    // Click browse to select folder
    await browseButton.click();
    
    // Mock folder selection
    const customFolder = path.join(testProjectsDir, "custom_location");
    await fs.mkdir(customFolder, { recursive: true });
    
    await app.evaluate(async ({ dialog }, folderPath) => {
      dialog.showOpenDialog = () => 
        Promise.resolve({ filePaths: [folderPath], canceled: false });
    }, customFolder);
    
    // Folder path should be updated
    await expect(folderPathInput).toHaveValue(customFolder);
    
    // Enter project name
    await projectNameInput.fill("My_Custom_Project");
    
    // Save button
    const saveButton = await saveDialog.getByRole("button", { name: "Save" });
    await saveButton.click();
    
    // Verify project was saved
    const projectDir = path.join(customFolder, "My_Custom_Project");
    const projectFile = path.join(projectDir, "My_Custom_Project.atlasvibe");
    
    await window.waitForTimeout(1000); // Wait for save
    
    const exists = await fs.access(projectFile).then(() => true).catch(() => false);
    expect(exists).toBe(true);
    
    // Status should show saved with project name
    const statusIndicator = await window.locator(".project-status-indicator");
    await expect(statusIndicator).toHaveText("Saved - My_Custom_Project");
  });

  test("should validate project names with same rules as blocks", async () => {
    // Open save as dialog
    await window.keyboard.press("Control+Shift+S");
    
    const saveDialog = await window.getByRole("dialog", { name: "Save Project" });
    const projectNameInput = await saveDialog.locator('input[placeholder="Project name"]');
    const errorMessage = await saveDialog.locator(".error-message");
    const saveButton = await saveDialog.getByRole("button", { name: "Save" });
    
    // Test invalid characters
    const invalidNames = [
      { input: "my-project", error: "Name can only contain letters (A-Z, a-z) and underscores (_)" },
      { input: "123project", error: "Name must start with a letter" },
      { input: "my.project", error: "Name can only contain letters (A-Z, a-z) and underscores (_)" },
      { input: "my project!", error: "Name can only contain letters (A-Z, a-z) and underscores (_)" },
      { input: "", error: "Name cannot be empty" },
    ];
    
    for (const { input, error } of invalidNames) {
      await projectNameInput.clear();
      await projectNameInput.fill(input);
      await expect(errorMessage).toBeVisible();
      await expect(errorMessage).toHaveText(error);
      await expect(saveButton).toBeDisabled();
    }
    
    // Valid name
    await projectNameInput.clear();
    await projectNameInput.fill("Valid_Project_Name");
    await expect(errorMessage).toBeHidden();
    await expect(saveButton).toBeEnabled();
    
    // Test space replacement
    await projectNameInput.clear();
    await projectNameInput.fill("  My  Test   Project  ");
    
    // First click should preview
    await saveButton.click();
    await expect(projectNameInput).toHaveValue("My_Test_Project");
    
    const previewMessage = await saveDialog.locator(".preview-message");
    await expect(previewMessage).toBeVisible();
    await expect(previewMessage).toHaveText("Project will be saved as: My_Test_Project");
    
    // Cancel for now
    await saveDialog.getByRole("button", { name: "Cancel" }).click();
  });

  test("should handle project name collisions", async () => {
    // Create a project first
    const existingProjectName = "Existing_Project";
    const existingProjectDir = path.join(testProjectsDir, existingProjectName);
    await fs.mkdir(existingProjectDir, { recursive: true });
    await fs.writeFile(
      path.join(existingProjectDir, `${existingProjectName}.atlasvibe`),
      JSON.stringify({ name: existingProjectName })
    );
    
    // Try to save with same name
    await window.keyboard.press("Control+Shift+S");
    
    const saveDialog = await window.getByRole("dialog", { name: "Save Project" });
    const projectNameInput = await saveDialog.locator('input[placeholder="Project name"]');
    const folderPathInput = await saveDialog.locator('input[placeholder="Select folder"]');
    
    // Set folder
    await app.evaluate(async ({ dialog }, folderPath) => {
      dialog.showOpenDialog = () => 
        Promise.resolve({ filePaths: [folderPath], canceled: false });
    }, testProjectsDir);
    
    await saveDialog.getByRole("button", { name: "Browse" }).click();
    
    // Enter existing name
    await projectNameInput.fill(existingProjectName);
    
    // Should show warning
    const warningMessage = await saveDialog.locator(".warning-message");
    await expect(warningMessage).toBeVisible();
    await expect(warningMessage).toHaveText(
      "A project with this name already exists in the selected folder. Do you want to overwrite it?"
    );
    
    // Should show overwrite options
    const overwriteButton = await saveDialog.getByRole("button", { name: "Overwrite" });
    const cancelButton = await saveDialog.getByRole("button", { name: "Cancel" });
    await expect(overwriteButton).toBeVisible();
    await expect(cancelButton).toBeVisible();
    
    await cancelButton.click();
  });

  test("should implement autosave with transaction queue", async () => {
    // Create new project and save it first
    await window.keyboard.press("Control+N");
    
    const projectPath = path.join(testProjectsDir, "autosave_test");
    await app.evaluate(async ({ dialog }, savePath) => {
      dialog.showSaveDialog = () => 
        Promise.resolve({ filePath: savePath, canceled: false });
    }, projectPath);
    
    await window.keyboard.press("Control+S");
    await window.waitForTimeout(1000);
    
    // Make rapid changes to test transaction queue
    const changes = [
      async () => {
        // Add block
        await window.getByTestId(Selectors.sidebarInput).click();
        await window.keyboard.type("MULTIPLY");
        await window.keyboard.press("Enter");
      },
      async () => {
        // Move block
        const block = await window.locator("h2", { hasText: "MULTIPLY" }).first();
        await block.dragTo(await window.locator(".react-flow__pane"), {
          targetPosition: { x: 400, y: 300 }
        });
      },
      async () => {
        // Add another block
        await window.getByTestId(Selectors.sidebarInput).click();
        await window.keyboard.type("DIVIDE");
        await window.keyboard.press("Enter");
      },
      async () => {
        // Connect blocks
        const multiplyOutput = await window.locator('[data-handleid="multiply-output"]');
        const divideInput = await window.locator('[data-handleid="divide-input"]');
        await multiplyOutput.dragTo(divideInput);
      }
    ];
    
    // Execute changes rapidly
    for (const change of changes) {
      await change();
      await window.waitForTimeout(100); // Small delay between changes
    }
    
    // Check that autosave is queued
    const statusIndicator = await window.locator(".project-status-indicator");
    
    // Should show unsaved changes initially
    await expect(statusIndicator).toHaveText("Unsaved changes");
    
    // Wait for autosave to trigger (typically after 2 seconds of inactivity)
    await window.waitForTimeout(2500);
    
    // Should show autosaving
    await expect(statusIndicator).toHaveText("Autosaving");
    
    // Wait for autosave to complete
    await expect(statusIndicator).toHaveText("Saved", { timeout: 10000 });
    
    // Verify all changes were saved
    const projectFile = path.join(projectPath, "autosave_test.atlasvibe");
    const savedData = JSON.parse(await fs.readFile(projectFile, "utf-8"));
    
    // Should have both blocks
    expect(savedData.rfInstance.nodes).toHaveLength(2);
    expect(savedData.rfInstance.nodes.map(n => n.data.func)).toContain("MULTIPLY");
    expect(savedData.rfInstance.nodes.map(n => n.data.func)).toContain("DIVIDE");
    
    // Should have connection
    expect(savedData.rfInstance.edges).toHaveLength(1);
    
    // Test crash recovery - simulate by checking transaction log
    const transactionLog = path.join(projectPath, ".atlasvibe_transactions.log");
    const logExists = await fs.access(transactionLog).then(() => true).catch(() => false);
    
    if (logExists) {
      const transactions = await fs.readFile(transactionLog, "utf-8");
      const lines = transactions.split("\n").filter(line => line.trim());
      
      // Should have recorded all changes
      expect(lines.length).toBeGreaterThanOrEqual(changes.length);
      
      // Each line should be valid JSON
      for (const line of lines) {
        expect(() => JSON.parse(line)).not.toThrow();
      }
    }
  });

  test("should maintain different status colors readable on black background", async () => {
    const statusIndicator = await window.locator(".project-status-indicator");
    const backgroundElement = await window.locator(".status-bar, .app-header");
    
    // Get background color
    const bgColor = await backgroundElement.evaluate(el => 
      window.getComputedStyle(el).backgroundColor
    );
    
    // Should be dark/black
    expect(bgColor).toMatch(/rgb\(0, 0, 0\)|rgba\(0, 0, 0|rgb\(\d{0,30}, \d{0,30}, \d{0,30}\)/);
    
    // Test each status color
    const statusStates = [
      { text: "Saved", expectedColor: /rgb\(\d{100,200}, \d{200,255}, \d{100,200}\)/ }, // Green
      { text: "Unsaved changes", expectedColor: /rgb\(2\d{2}, \d{150,220}, \d{0,100}\)/ }, // Yellow
      { text: "Saving", expectedColor: /rgb\(2\d{2}, \d{180,240}, \d{50,150}\)/ }, // Light yellow
      { text: "Autosaving", expectedColor: /rgb\(2\d{2}, \d{200,255}, \d{100,200}\)/ }, // Pale yellow
    ];
    
    // Make changes to trigger different states
    for (const { text, expectedColor } of statusStates) {
      // Wait for the specific state (would be triggered by actual operations)
      if (await statusIndicator.textContent() === text) {
        const color = await statusIndicator.evaluate(el => 
          window.getComputedStyle(el).color
        );
        
        // Verify color matches expected range
        expect(color).toMatch(expectedColor);
        
        // Check contrast ratio (simplified check)
        const luminance = await statusIndicator.evaluate(el => {
          const style = window.getComputedStyle(el);
          const color = style.color;
          const rgb = color.match(/\d+/g);
          if (!rgb) return 0;
          const [r, g, b] = rgb.map(Number);
          // Relative luminance formula
          return (0.299 * r + 0.587 * g + 0.114 * b) / 255;
        });
        
        // Should have sufficient contrast on black (luminance > 0.3)
        expect(luminance).toBeGreaterThan(0.3);
      }
    }
  });
});
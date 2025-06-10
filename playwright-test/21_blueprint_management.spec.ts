#!/usr/bin/env node
// -*- coding: utf-8 -*-

// HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
// - New test file for blueprint management functionality
// - Tests saving blocks as blueprints
// - Tests blueprint renaming with validation
// - Tests name collision detection
// - Tests automatic space replacement with underscores
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

let app: ElectronApplication;
let window: Page;

test.describe("Blueprint Management", () => {
  test.beforeAll(async () => {
    test.setTimeout(STARTUP_TIMEOUT);
    const executablePath = getExecutablePath();
    app = await electron.launch({ executablePath });
    await mockDialogMessage(app);
    window = await app.firstWindow();
    
    await window.waitForSelector(Selectors.closeWelcomeModalBtn, { timeout: 30000 });
    await window.getByTestId(Selectors.closeWelcomeModalBtn).click();
  });

  test.afterAll(async () => {
    await writeLogFile(app, "blueprint-management");
    await app.close();
  });

  test("should save custom block as blueprint in global palette", async () => {
    // Create a custom block first
    await window.getByTestId(Selectors.sidebarInput).click();
    await window.keyboard.type("ADD");
    await window.keyboard.press("Enter");
    
    const addBlock = await window.locator("h2", { hasText: "ADD" }).first();
    await expect(addBlock).toBeVisible();
    
    // Modify it to make it custom
    await addBlock.click({ button: "right" });
    await window.getByTestId(Selectors.contextEditBlockBtn).click();
    
    // Make a change
    await window.keyboard.type("# Custom modification");
    await window.keyboard.press("Control+S");
    
    // Close editor
    await window.keyboard.press("Escape");
    
    // Right-click and select "Save as Blueprint"
    await addBlock.click({ button: "right" });
    const saveAsBlueprintOption = await window.locator("text=Save as Blueprint");
    await expect(saveAsBlueprintOption).toBeVisible();
    await saveAsBlueprintOption.click();
    
    // Enter blueprint name
    const nameDialog = await window.getByRole("dialog");
    await expect(nameDialog).toBeVisible();
    
    const nameInput = await nameDialog.locator('input[placeholder="Enter blueprint name"]');
    await nameInput.fill("MY_CUSTOM_ADD");
    
    // Click Save
    await nameDialog.getByRole("button", { name: "Save" }).click();
    
    // Verify blueprint appears in global palette
    await window.getByTestId(Selectors.sidebarInput).click();
    await window.keyboard.type("MY_CUSTOM_ADD");
    
    const blueprintOption = await window.locator(".sidebar-item", { hasText: "MY_CUSTOM_ADD" });
    await expect(blueprintOption).toBeVisible();
    
    // Verify it's marked as a blueprint
    const blueprintBadge = await blueprintOption.locator(".blueprint-badge");
    await expect(blueprintBadge).toBeVisible();
    await expect(blueprintBadge).toHaveText("Blueprint");
  });

  test("should validate blueprint names with only letters and underscores", async () => {
    // Create a block to save as blueprint
    await window.getByTestId(Selectors.sidebarInput).click();
    await window.keyboard.type("MULTIPLY");
    await window.keyboard.press("Enter");
    
    const block = await window.locator("h2", { hasText: "MULTIPLY" }).first();
    await block.click({ button: "right" });
    await window.locator("text=Save as Blueprint").click();
    
    const nameDialog = await window.getByRole("dialog");
    const nameInput = await nameDialog.locator('input[placeholder="Enter blueprint name"]');
    const errorMessage = await nameDialog.locator(".error-message");
    
    // Test invalid characters
    await nameInput.fill("MY-BLOCK-123!");
    await expect(errorMessage).toBeVisible();
    await expect(errorMessage).toHaveText("Name can only contain letters (A-Z, a-z) and underscores (_)");
    
    // Save button should be disabled
    const saveButton = await nameDialog.getByRole("button", { name: "Save" });
    await expect(saveButton).toBeDisabled();
    
    // Test valid name
    await nameInput.clear();
    await nameInput.fill("MY_VALID_BLOCK");
    await expect(errorMessage).toBeHidden();
    await expect(saveButton).toBeEnabled();
    
    // Test starting with number
    await nameInput.clear();
    await nameInput.fill("123_BLOCK");
    await expect(errorMessage).toBeVisible();
    await expect(errorMessage).toHaveText("Name must start with a letter");
    
    // Test empty name
    await nameInput.clear();
    await expect(errorMessage).toBeVisible();
    await expect(errorMessage).toHaveText("Name cannot be empty");
  });

  test("should detect name collisions when saving blueprints", async () => {
    // First, save a blueprint
    await window.getByTestId(Selectors.sidebarInput).click();
    await window.keyboard.type("DIVIDE");
    await window.keyboard.press("Enter");
    
    const firstBlock = await window.locator("h2", { hasText: "DIVIDE" }).first();
    await firstBlock.click({ button: "right" });
    await window.locator("text=Save as Blueprint").click();
    
    const firstDialog = await window.getByRole("dialog");
    await firstDialog.locator('input[placeholder="Enter blueprint name"]').fill("UNIQUE_DIVIDER");
    await firstDialog.getByRole("button", { name: "Save" }).click();
    
    // Try to save another with the same name
    await window.getByTestId(Selectors.sidebarInput).click();
    await window.keyboard.type("SUBTRACT");
    await window.keyboard.press("Enter");
    
    const secondBlock = await window.locator("h2", { hasText: "SUBTRACT" }).first();
    await secondBlock.click({ button: "right" });
    await window.locator("text=Save as Blueprint").click();
    
    const secondDialog = await window.getByRole("dialog");
    const nameInput = await secondDialog.locator('input[placeholder="Enter blueprint name"]');
    await nameInput.fill("UNIQUE_DIVIDER");
    
    // Should show collision warning
    const warningMessage = await secondDialog.locator(".warning-message");
    await expect(warningMessage).toBeVisible();
    await expect(warningMessage).toHaveText("A blueprint with this name already exists. Do you want to overwrite it?");
    
    // Should show additional confirmation buttons
    const overwriteButton = await secondDialog.getByRole("button", { name: "Overwrite" });
    const cancelButton = await secondDialog.getByRole("button", { name: "Cancel" });
    await expect(overwriteButton).toBeVisible();
    await expect(cancelButton).toBeVisible();
    
    // Test cancel
    await cancelButton.click();
    await expect(secondDialog).toBeHidden();
  });

  test("should automatically replace spaces with underscores in names", async () => {
    await window.getByTestId(Selectors.sidebarInput).click();
    await window.keyboard.type("POWER");
    await window.keyboard.press("Enter");
    
    const block = await window.locator("h2", { hasText: "POWER" }).first();
    await block.click({ button: "right" });
    await window.locator("text=Save as Blueprint").click();
    
    const dialog = await window.getByRole("dialog");
    const nameInput = await dialog.locator('input[placeholder="Enter blueprint name"]');
    const saveButton = await dialog.getByRole("button", { name: "Save" });
    
    // Type name with spaces
    await nameInput.fill("  My  Custom   Block  ");
    
    // First click should preview the cleaned name
    await saveButton.click();
    
    // Input should show cleaned name
    await expect(nameInput).toHaveValue("My_Custom_Block");
    
    // Should show preview message
    const previewMessage = await dialog.locator(".preview-message");
    await expect(previewMessage).toBeVisible();
    await expect(previewMessage).toHaveText("Name will be saved as: My_Custom_Block");
    
    // Second click should actually save
    await saveButton.click();
    await expect(dialog).toBeHidden();
    
    // Verify blueprint was saved with cleaned name
    await window.getByTestId(Selectors.sidebarInput).click();
    await window.keyboard.type("My_Custom_Block");
    const savedBlueprint = await window.locator(".sidebar-item", { hasText: "My_Custom_Block" });
    await expect(savedBlueprint).toBeVisible();
  });

  test("should allow renaming blueprints via UI", async () => {
    // Create and save a blueprint first
    await window.getByTestId(Selectors.sidebarInput).click();
    await window.keyboard.type("LOG");
    await window.keyboard.press("Enter");
    
    const block = await window.locator("h2", { hasText: "LOG" }).first();
    await block.click({ button: "right" });
    await window.locator("text=Save as Blueprint").click();
    
    const saveDialog = await window.getByRole("dialog");
    await saveDialog.locator('input[placeholder="Enter blueprint name"]').fill("OLD_NAME_BLOCK");
    await saveDialog.getByRole("button", { name: "Save" }).click();
    
    // Open blueprint manager
    await window.getByTestId("blueprintManagerBtn").click();
    const blueprintManager = await window.getByRole("dialog", { name: "Blueprint Manager" });
    await expect(blueprintManager).toBeVisible();
    
    // Find the blueprint
    const blueprintItem = await blueprintManager.locator(".blueprint-item", { hasText: "OLD_NAME_BLOCK" });
    await expect(blueprintItem).toBeVisible();
    
    // Click rename button
    const renameButton = await blueprintItem.locator(".rename-button");
    await renameButton.click();
    
    // Rename dialog appears
    const renameDialog = await window.getByRole("dialog", { name: "Rename Blueprint" });
    const renameInput = await renameDialog.locator('input[placeholder="Enter new name"]');
    
    // Current name should be pre-filled
    await expect(renameInput).toHaveValue("OLD_NAME_BLOCK");
    
    // Enter new name with spaces
    await renameInput.clear();
    await renameInput.fill("New Name Block");
    
    // First click previews
    const confirmButton = await renameDialog.getByRole("button", { name: "Rename" });
    await confirmButton.click();
    
    await expect(renameInput).toHaveValue("New_Name_Block");
    
    // Second click applies
    await confirmButton.click();
    
    // Verify rename
    await expect(blueprintItem).not.toBeVisible();
    const renamedItem = await blueprintManager.locator(".blueprint-item", { hasText: "New_Name_Block" });
    await expect(renamedItem).toBeVisible();
    
    // Close manager
    await blueprintManager.getByRole("button", { name: "Close" }).click();
    
    // Verify in palette
    await window.getByTestId(Selectors.sidebarInput).click();
    await window.keyboard.type("New_Name_Block");
    const paletteItem = await window.locator(".sidebar-item", { hasText: "New_Name_Block" });
    await expect(paletteItem).toBeVisible();
  });

  test("should handle name validation during rename", async () => {
    // Assume we have blueprint manager open with a blueprint
    await window.getByTestId("blueprintManagerBtn").click();
    const blueprintManager = await window.getByRole("dialog", { name: "Blueprint Manager" });
    
    // Create a test blueprint if needed
    const testBlueprint = await blueprintManager.locator(".blueprint-item").first();
    const renameButton = await testBlueprint.locator(".rename-button");
    await renameButton.click();
    
    const renameDialog = await window.getByRole("dialog", { name: "Rename Blueprint" });
    const renameInput = await renameDialog.locator('input[placeholder="Enter new name"]');
    const errorMessage = await renameDialog.locator(".error-message");
    
    // Test various invalid inputs
    const invalidNames = [
      { input: "", error: "Name cannot be empty" },
      { input: "123Start", error: "Name must start with a letter" },
      { input: "has-dashes", error: "Name can only contain letters (A-Z, a-z) and underscores (_)" },
      { input: "has.dots", error: "Name can only contain letters (A-Z, a-z) and underscores (_)" },
      { input: "has@special#chars!", error: "Name can only contain letters (A-Z, a-z) and underscores (_)" },
    ];
    
    for (const { input, error } of invalidNames) {
      await renameInput.clear();
      await renameInput.fill(input);
      await expect(errorMessage).toBeVisible();
      await expect(errorMessage).toHaveText(error);
      
      // Rename button should be disabled
      const renameBtn = await renameDialog.getByRole("button", { name: "Rename" });
      await expect(renameBtn).toBeDisabled();
    }
    
    // Valid name should enable button
    await renameInput.clear();
    await renameInput.fill("VALID_NAME");
    await expect(errorMessage).toBeHidden();
    const renameBtn = await renameDialog.getByRole("button", { name: "Rename" });
    await expect(renameBtn).toBeEnabled();
  });
});
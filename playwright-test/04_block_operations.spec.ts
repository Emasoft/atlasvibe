// Copyright (c) 2024 Emasoft (for atlasvibe modifications and derivative work)
// Copyright (c) 2024 Flojoy (for the original "Flojoy Studio" software)
//
// This software is licensed under the MIT License.
// Refer to the LICENSE file for more details.

import { test, expect, Page } from "@playwright/test";
import { Selectors, blockPaletteSelectors, flowchartSelectors } from "./selectors";
import { ElectronAppInfo, launchApp, newProject } from "./utils"; 

let appInfo: ElectronAppInfo;

test.beforeAll(async () => {
  appInfo = await launchApp();
});

test.afterAll(async () => {
  if (appInfo && appInfo.app) {
    await appInfo.app.close();
  }
});

test.describe("Block Operations on Flowchart", () => {
  let page: Page;

  test.beforeEach(async () => {
    page = appInfo.page;
    const closeWelcomeBtn = page.locator(`button[data-testid='${Selectors.closeWelcomeModalBtn}']`);
    if (await closeWelcomeBtn.isVisible({timeout: 2000}).catch(() => false)) {
        await closeWelcomeBtn.click();
    }
    await newProject(page, `BlockOpsTest-${Date.now()}`); // Unique project name for each test run
  });

  test("Add multiple blueprint blocks creates custom blocks with incrementing default suffixed names", async () => {
    const blueprintKey = "MATRIX_VIEW"; 
    const expectedFirstName = `${blueprintKey}_1`;
    const expectedSecondName = `${blueprintKey}_2`;
    const expectedThirdName = `${blueprintKey}_3`;

    const paletteBlock = page.locator(blockPaletteSelectors.blockByTestId(blueprintKey));
    await expect(paletteBlock).toBeVisible({ timeout: 10000 });
    
    // Add first block
    await paletteBlock.dragTo(page.locator(Selectors.flowchartCanvas), { targetPosition: { x: 50, y: 50 } });
    const firstNodeLabel = page.locator(flowchartSelectors.nodeLabelByName(expectedFirstName));
    await expect(firstNodeLabel).toBeVisible();
    await expect(firstNodeLabel).toHaveText(expectedFirstName);

    // Add second block
    await paletteBlock.dragTo(page.locator(Selectors.flowchartCanvas), { targetPosition: { x: 50, y: 150 } });
    const secondNodeLabel = page.locator(flowchartSelectors.nodeLabelByName(expectedSecondName));
    await expect(secondNodeLabel).toBeVisible();
    await expect(secondNodeLabel).toHaveText(expectedSecondName);
    
    // Add third block
    await paletteBlock.dragTo(page.locator(Selectors.flowchartCanvas), { targetPosition: { x: 50, y: 250 } });
    const thirdNodeLabel = page.locator(flowchartSelectors.nodeLabelByName(expectedThirdName));
    await expect(thirdNodeLabel).toBeVisible();
    await expect(thirdNodeLabel).toHaveText(expectedThirdName);
  });

  test("Rename a custom block successfully", async () => {
    const blueprintKey = "CONSTANT";
    const initialName = `${blueprintKey}_1`;
    const newName = "MySpecificConstant";

    const paletteBlock = page.locator(blockPaletteSelectors.blockByTestId(blueprintKey));
    await paletteBlock.dragTo(page.locator(Selectors.flowchartCanvas));
    const nodeLabel = page.locator(flowchartSelectors.nodeLabelByName(initialName));
    await expect(nodeLabel).toBeVisible();

    await nodeLabel.click(); // Open properties panel
    const nameInput = page.locator(Selectors.propertiesPanelBlockNameInput);
    await expect(nameInput).toBeVisible();
    await expect(nameInput).toHaveValue(initialName);
    await nameInput.fill(newName);
    await page.locator(Selectors.flowchartCanvas).click({ position: { x: 0, y: 0 } }); // Blur to apply

    const renamedNodeLabel = page.locator(flowchartSelectors.nodeLabelByName(newName));
    await expect(renamedNodeLabel).toBeVisible();
    await expect(renamedNodeLabel).toHaveText(newName);
    await expect(nodeLabel).not.toBeVisible(); // Old name should be gone
  });

  test("Rename a block to an empty string should be prevented or handled", async () => {
    const blueprintKey = "CONSTANT";
    const initialName = `${blueprintKey}_1`;

    const paletteBlock = page.locator(blockPaletteSelectors.blockByTestId(blueprintKey));
    await paletteBlock.dragTo(page.locator(Selectors.flowchartCanvas));
    const nodeLabel = page.locator(flowchartSelectors.nodeLabelByName(initialName));
    await nodeLabel.click();

    const nameInput = page.locator(Selectors.propertiesPanelBlockNameInput);
    await nameInput.fill(""); // Try to set empty name
    await page.locator(Selectors.flowchartCanvas).click({ position: { x: 0, y: 0 } });

    // Expected behavior: Name reverts to original, or an error is shown, or input is invalid.
    // For this test, let's assume it reverts or stays the same.
    await expect(page.locator(flowchartSelectors.nodeLabelByName(initialName))).toBeVisible();
    // Add assertion for error message if applicable:
    // const errorMessage = page.locator("div[data-testid='error-message-name-empty']");
    // await expect(errorMessage).toBeVisible();
  });
  
  test("Rename a block to a name with special characters (UI should handle/sanitize or backend reject)", async () => {
    const blueprintKey = "CONSTANT";
    const initialName = `${blueprintKey}_1`;
    const specialName = "My@#$Constant"; // Potentially problematic name
    const sanitizedOrExpectedName = "MyConstant"; // Example of sanitized name, or it might take specialName

    const paletteBlock = page.locator(blockPaletteSelectors.blockByTestId(blueprintKey));
    await paletteBlock.dragTo(page.locator(Selectors.flowchartCanvas));
    await page.locator(flowchartSelectors.nodeLabelByName(initialName)).click();

    const nameInput = page.locator(Selectors.propertiesPanelBlockNameInput);
    await nameInput.fill(specialName);
    await page.locator(Selectors.flowchartCanvas).click({ position: { x: 0, y: 0 } });

    // Behavior depends on implementation:
    // 1. UI sanitizes it (e.g., to "MyConstant")
    // 2. UI allows it, backend handles/rejects (test backend separately)
    // 3. UI shows validation error
    // Assuming for now it might be sanitized or accepted, then check visibility.
    // This test would need adjustment based on actual sanitization/validation rules.
    const finalNodeLabel = page.locator(flowchartSelectors.nodeLabelByName(sanitizedOrExpectedName)); // Or specialName
    // await expect(finalNodeLabel).toBeVisible();
    // await expect(finalNodeLabel).toHaveText(sanitizedOrExpectedName); // Or specialName
    // OR check for validation error message
    // For now, just ensure the app doesn't crash and the original name might persist if invalid
    await expect(page.locator(flowchartSelectors.nodeLabelByName(initialName))).toBeVisible(); // Fallback check
  });


  test("Rename collision with a blueprint key should result in suffixed name", async () => {
    const blueprintKey = "CONSTANT";
    const initialName = `${blueprintKey}_1`;
    const collidingBlueprintName = "ADD"; // Assumed to be another blueprint key
    const expectedSuffixedName = `${collidingBlueprintName}_1`;

    const paletteBlock = page.locator(blockPaletteSelectors.blockByTestId(blueprintKey));
    await paletteBlock.dragTo(page.locator(Selectors.flowchartCanvas));
    await page.locator(flowchartSelectors.nodeLabelByName(initialName)).click();
    
    const nameInput = page.locator(Selectors.propertiesPanelBlockNameInput);
    await nameInput.fill(collidingBlueprintName);
    await page.locator(Selectors.flowchartCanvas).click({ position: { x: 0, y: 0 } });

    const finalNodeLabel = page.locator(flowchartSelectors.nodeLabelByName(expectedSuffixedName));
    await expect(finalNodeLabel).toBeVisible({ timeout: 5000 }); 
    await expect(finalNodeLabel).toHaveText(expectedSuffixedName);
  });

  test("Rename collision with an existing custom block name should result in suffixed name", async () => {
    const blueprintKey1 = "CONSTANT";
    const block1InitialName = `${blueprintKey1}_1`;
    
    const blueprintKey2 = "ADD"; // Different blueprint
    const block2InitialName = `${blueprintKey2}_1`;
    
    const expectedSuffixedNameAfterCollision = `${block1InitialName}_1`;

    const paletteBlock1 = page.locator(blockPaletteSelectors.blockByTestId(blueprintKey1));
    await paletteBlock1.dragTo(page.locator(Selectors.flowchartCanvas), { targetPosition: { x: 50, y: 50 } });
    const paletteBlock2 = page.locator(blockPaletteSelectors.blockByTestId(blueprintKey2));
    await paletteBlock2.dragTo(page.locator(Selectors.flowchartCanvas), { targetPosition: { x: 50, y: 150 } });

    const block1Label = page.locator(flowchartSelectors.nodeLabelByName(block1InitialName));
    const block2Label = page.locator(flowchartSelectors.nodeLabelByName(block2InitialName));
    await expect(block1Label).toBeVisible();
    await expect(block2Label).toBeVisible();

    await block2Label.click(); // Select block2
    const nameInput = page.locator(Selectors.propertiesPanelBlockNameInput);
    await nameInput.fill(block1InitialName); // Try to rename block2 to block1's name
    await page.locator(Selectors.flowchartCanvas).click({ position: { x: 0, y: 0 } });

    const finalNodeLabel = page.locator(flowchartSelectors.nodeLabelByName(expectedSuffixedNameAfterCollision));
    await expect(finalNodeLabel).toBeVisible({ timeout: 5000 });
    await expect(finalNodeLabel).toHaveText(expectedSuffixedNameAfterCollision);
    await expect(block1Label).toBeVisible(); // Original block1 should still exist
  });

  test("Rename block, then rename another block to the original name of the first", async () => {
    const constBlueprintKey = "CONSTANT";
    const addBlueprintKey = "ADD";

    const constBlockOriginalName = `${constBlueprintKey}_1`;
    const constBlockNewName = "MyUniqueConst";
    const addBlockOriginalName = `${addBlueprintKey}_1`;

    // Add CONSTANT_1
    await page.locator(blockPaletteSelectors.blockByTestId(constBlueprintKey)).dragTo(page.locator(Selectors.flowchartCanvas), { targetPosition: { x: 50, y: 50 } });
    const constNodeLabel = page.locator(flowchartSelectors.nodeLabelByName(constBlockOriginalName));
    await expect(constNodeLabel).toBeVisible();

    // Rename CONSTANT_1 to MyUniqueConst
    await constNodeLabel.click();
    await page.locator(Selectors.propertiesPanelBlockNameInput).fill(constBlockNewName);
    await page.locator(Selectors.flowchartCanvas).click({ position: { x: 0, y: 0 } });
    await expect(page.locator(flowchartSelectors.nodeLabelByName(constBlockNewName))).toBeVisible();
    await expect(constNodeLabel).not.toBeVisible(); // CONSTANT_1 is gone

    // Add ADD_1
    await page.locator(blockPaletteSelectors.blockByTestId(addBlueprintKey)).dragTo(page.locator(Selectors.flowchartCanvas), { targetPosition: { x: 50, y: 150 } });
    const addNodeLabel = page.locator(flowchartSelectors.nodeLabelByName(addBlockOriginalName));
    await expect(addNodeLabel).toBeVisible();
    
    // Rename ADD_1 to CONSTANT_1 (which is now available)
    await addNodeLabel.click();
    await page.locator(Selectors.propertiesPanelBlockNameInput).fill(constBlockOriginalName); // Target: CONSTANT_1
    await page.locator(Selectors.flowchartCanvas).click({ position: { x: 0, y: 0 } });

    // ADD_1 should now be named CONSTANT_1
    await expect(page.locator(flowchartSelectors.nodeLabelByName(constBlockOriginalName))).toBeVisible();
    await expect(addNodeLabel).not.toBeVisible(); // ADD_1 is gone
  });
});

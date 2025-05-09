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

  test("Rename a block to an empty string should revert to original name", async () => {
    const blueprintKey = "CONSTANT";
    const initialName = `${blueprintKey}_1`;

    const paletteBlock = page.locator(blockPaletteSelectors.blockByTestId(blueprintKey));
    await paletteBlock.dragTo(page.locator(Selectors.flowchartCanvas));
    const nodeLabel = page.locator(flowchartSelectors.nodeLabelByName(initialName));
    await nodeLabel.click();

    const nameInput = page.locator(Selectors.propertiesPanelBlockNameInput);
    await expect(nameInput).toBeVisible();
    await nameInput.fill(""); // Try to set empty name
    await page.locator(Selectors.flowchartCanvas).click({ position: { x: 0, y: 0 } }); // Blur to apply

    // Expected behavior: Name reverts to original, or an error is shown.
    // Assuming it reverts to the original name if input is invalid or empty.
    const currentNodeLabel = page.locator(flowchartSelectors.nodeLabelByName(initialName));
    await expect(currentNodeLabel).toBeVisible();
    await expect(currentNodeLabel).toHaveText(initialName);
    // If an error message is expected:
    // const errorMessage = page.locator("div[data-testid='error-message-name-empty']"); // Adjust selector
    // await expect(errorMessage).toBeVisible();
  });
  
  test("Rename a block to a name with special characters", async () => {
    const blueprintKey = "CONSTANT";
    const initialName = `${blueprintKey}_1`;
    const specialName = "My@Sp€ci@l_N@me#1"; // Name with various special characters

    const paletteBlock = page.locator(blockPaletteSelectors.blockByTestId(blueprintKey));
    await paletteBlock.dragTo(page.locator(Selectors.flowchartCanvas));
    await page.locator(flowchartSelectors.nodeLabelByName(initialName)).click();

    const nameInput = page.locator(Selectors.propertiesPanelBlockNameInput);
    await expect(nameInput).toBeVisible();
    await nameInput.fill(specialName);
    await page.locator(Selectors.flowchartCanvas).click({ position: { x: 0, y: 0 } }); // Blur to apply

    // Behavior depends on implementation:
    // 1. UI accepts it as is, backend handles/rejects/sanitizes.
    // 2. UI sanitizes it before sending to backend.
    // 3. UI shows validation error and name reverts or doesn't change.
    // This test assumes the name is accepted as is by the UI, and backend would handle it.
    // Or, if there's client-side validation that prevents it, the name would revert.
    // For this test, we'll check if the node label reflects the specialName.
    // This might need adjustment based on actual sanitization/validation rules.
    const finalNodeLabel = page.locator(flowchartSelectors.nodeLabelByName(specialName));
    const initialNodeLabelStillVisible = page.locator(flowchartSelectors.nodeLabelByName(initialName));

    // Check if either the new special name is applied OR the name reverted to initial
    // This is a common pattern if validation is strict and reverts on invalid input.
    const newNameApplied = await finalNodeLabel.isVisible({timeout: 1000}).catch(() => false);
    if (newNameApplied) {
        await expect(finalNodeLabel).toHaveText(specialName);
    } else {
        await expect(initialNodeLabelStillVisible).toBeVisible();
        await expect(initialNodeLabelStillVisible).toHaveText(initialName);
        // Optionally, check for a validation error message here if that's the expected behavior
    }
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
    await expect(nameInput).toBeVisible();
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
    await expect(nameInput).toBeVisible();
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
    const nameInput = page.locator(Selectors.propertiesPanelBlockNameInput);
    await expect(nameInput).toBeVisible();
    await nameInput.fill(constBlockNewName);
    await page.locator(Selectors.flowchartCanvas).click({ position: { x: 0, y: 0 } });
    await expect(page.locator(flowchartSelectors.nodeLabelByName(constBlockNewName))).toBeVisible();
    await expect(constNodeLabel).not.toBeVisible(); // CONSTANT_1 is gone

    // Add ADD_1
    await page.locator(blockPaletteSelectors.blockByTestId(addBlueprintKey)).dragTo(page.locator(Selectors.flowchartCanvas), { targetPosition: { x: 50, y: 150 } });
    const addNodeLabel = page.locator(flowchartSelectors.nodeLabelByName(addBlockOriginalName));
    await expect(addNodeLabel).toBeVisible();
    
    // Rename ADD_1 to CONSTANT_1 (which is now available)
    await addNodeLabel.click();
    await nameInput.fill(constBlockOriginalName); // Target: CONSTANT_1
    await page.locator(Selectors.flowchartCanvas).click({ position: { x: 0, y: 0 } });

    // ADD_1 should now be named CONSTANT_1
    await expect(page.locator(flowchartSelectors.nodeLabelByName(constBlockOriginalName))).toBeVisible();
    await expect(addNodeLabel).not.toBeVisible(); // ADD_1 is gone
  });
});

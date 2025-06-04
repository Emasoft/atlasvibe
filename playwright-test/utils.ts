// Copyright (c) 2024 Emasoft (for atlasvibe modifications and derivative work)
// Copyright (c) 2024 Atlasvibe (for the original "Atlasvibe Studio" software)
//
// This software is licensed under the MIT License.
// Refer to the LICENSE file for more details.

import { execSync } from "child_process";
import { join } from "path";
import fs from "fs";
import { ElectronApplication, Page, _electron as electron, expect } from "playwright"; // Added expect
import { Selectors } from "./selectors"; // Assuming Selectors enum is in selectors.ts

export const STARTUP_TIMEOUT = 300000; // 5 mins
export const standbyStatus = "🐢 awaiting a new job"; // This might need rebranding if it's a visible string

export interface ElectronAppInfo {
  app: ElectronApplication;
  page: Page;
  appPath: string;
}

export const getExecutablePath = () => {
  const appName = "atlasvibe"; // Rebranded app name
  switch (process.platform) {
    case "darwin":
      return join(
        process.cwd(),
        `dist/mac-universal/${appName}.app/Contents/MacOS/${appName}`,
      );
    case "win32": {
      const arch = process.arch;
      const folderName =
        arch === "arm64" ? `win-${arch}-unpacked` : "win-unpacked";
      return join(process.cwd(), `dist/${folderName}/${appName}.exe`);
    }
    case "linux": {
      const arch = process.arch;
      const folderName = `linux-${arch === "arm64" ? `${arch}-` : ""}unpacked`;
      const appPath = join(process.cwd(), `dist/${folderName}/${appName}`); // Rebranded executable name
      execSync(`chmod +x "${appPath}"`);
      return appPath;
    }
    default:
      throw new Error("Unrecognized platform: " + process.platform);
  }
};

export const launchApp = async (): Promise<ElectronAppInfo> => {
  const appPath = getExecutablePath();
  const app = await electron.launch({
    executablePath: appPath,
    args: ["."], // Add any necessary startup arguments
  });
  const page = await app.firstWindow();
  await page.waitForLoadState("domcontentloaded");

  // Example: Close welcome modal if it exists
  const closeWelcomeBtn = page.locator(`button[data-testid='${Selectors.closeWelcomeModalBtn}']`);
    if (await closeWelcomeBtn.isVisible({timeout: 5000}).catch(() => false)) { // Increased timeout slightly
        await closeWelcomeBtn.click();
  }
  // Handle "Existing Server Detected" dialog
  await mockDialogMessage(app);

  return { app, page, appPath };
};

export const writeLogFile = async (
  app: ElectronApplication,
  testName: string,
) => {
  const logPath = await app.evaluate(async ({ app: _app }) => {
    return _app.getPath("logs");
  });
  const logFile = join(logPath, "main.log"); // Assuming main.log is the correct log file name
  if (fs.existsSync(logFile)) {
    const logs = fs.readFileSync(logFile);
    fs.writeFileSync(
      `test-results/${process.platform}-${testName}-logs.txt`,
      logs,
    );
  } else {
    console.warn(`Log file not found at ${logFile} for test ${testName}`);
  }
};

export const mockDialogMessage = async (app: ElectronApplication) => {
  await app.evaluate(async ({ dialog }) => {
    const originalShowMessageBoxSync = dialog.showMessageBoxSync;

    // Create a wrapper function with the original signature
    const wrapperShowMessageBoxSync = (
      browserWindow: Electron.BrowserWindow | undefined,
      options: Electron.MessageBoxSyncOptions,
    ) => {
      if (options.title === "Existing Server Detected") { // This title might need rebranding if it changed
        return 1; // Simulate clicking the second button (e.g., "Use Existing")
      } else {
        return browserWindow
          ? originalShowMessageBoxSync(browserWindow, options)
          : originalShowMessageBoxSync(options);
      }
    };
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    dialog.showMessageBoxSync = wrapperShowMessageBoxSync as any;
  });
};

export const newProject = async (page: Page, projectName: string): Promise<void> => {
  // This function assumes a UI flow for creating a new project.
  // Adjust selectors and actions based on your application's actual UI.

  // Option 1: Direct "New Project" button if available
  const newProjectBtn = page.locator(`button[data-testid='${Selectors.projectNewProjectButton}']`);
  const fileMenuBtn = page.locator(`button[data-testid='${Selectors.fileBtn}']`);

  if (await newProjectBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
    await newProjectBtn.click();
  } else if (await fileMenuBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
    // Option 2: Via File menu -> New (dropdown)
    await fileMenuBtn.click();
    // Assuming 'newDropdown' is the correct selector for the "New Project" item in the dropdown.
    // This might need to be more specific, e.g., a menu item with text "New Project".
    const newDropdownItem = page.locator(`[data-testid='${Selectors.newDropdown}']`); // Or a more specific selector for "New Project"
    await expect(newDropdownItem).toBeVisible();
    await newDropdownItem.click();
  } else {
    throw new Error("Could not find a button/menu to initiate new project creation.");
  }

  // Modal for new project name
  const projectNameInput = page.locator(`input[data-testid='${Selectors.projectProjectNameInput}']`);
  await expect(projectNameInput).toBeVisible({ timeout: 5000 }); // Wait for modal to appear
  await projectNameInput.fill(projectName);

  const createButton = page.locator(`button[data-testid='${Selectors.projectCreateProjectModalButton}']`);
  await expect(createButton).toBeVisible();
  await createButton.click();

  // Add a small wait or an assertion to ensure the project is created and UI is ready
  // For example, wait for the project name to appear in the title bar or a specific UI element.
  // This depends on your app's behavior after project creation.
  // Example: Ensure the canvas is clear or a specific project title element is updated.
  // await expect(page.locator(Selectors.flowchartCanvas)).toBeEmpty({ timeout: 5000 }); // If canvas should be empty
  // await expect(page.locator(`[data-testid='${Selectors.appTitle}']`)).toHaveText(projectName, { timeout: 5000 }); // If app title shows project name
  await page.waitForTimeout(500); // A small delay to allow UI to settle, prefer explicit waits on elements.
};

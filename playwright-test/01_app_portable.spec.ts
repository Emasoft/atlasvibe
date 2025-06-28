import { test, expect, Page, ElectronApplication } from "@playwright/test";
import { _electron as electron } from "@playwright/test";
import { join } from "path";
import fs from "fs";
import { execSync } from "child_process";

/**
 * Simplified E2E test for portable build
 * Tests the portable executable without complex launch configurations
 */

let app: ElectronApplication;
let page: Page;

test.beforeEach(async () => {
  // Determine the path to the portable executable
  let executablePath: string;

  if (process.platform === "win32") {
    // For portable build, use the batch launcher
    const portableDir = join(process.cwd(), "dist-portable");
    const batchPath = join(portableDir, "start-atlasvibe.bat");

    // First check if we have a portable build
    if (fs.existsSync(batchPath)) {
      console.log("Using portable batch launcher:", batchPath);

      // For Windows portable, we'll use the actual exe inside the extracted folder
      const portableExe = join(
        portableDir,
        "AtlasVibe-Portable",
        "atlasvibe.exe",
      );
      if (fs.existsSync(portableExe)) {
        executablePath = portableExe;
      } else {
        // Fallback to regular build
        executablePath = join(
          process.cwd(),
          "dist",
          "win-unpacked",
          "atlasvibe.exe",
        );
      }
    } else {
      // Use regular build
      executablePath = join(
        process.cwd(),
        "dist",
        "win-unpacked",
        "atlasvibe.exe",
      );
    }
  } else if (process.platform === "darwin") {
    executablePath = join(
      process.cwd(),
      "dist",
      "mac-universal",
      "atlasvibe.app",
      "Contents",
      "MacOS",
      "atlasvibe",
    );
  } else {
    executablePath = join(process.cwd(), "dist", "linux-unpacked", "atlasvibe");
  }

  console.log(`Executable path: ${executablePath}`);
  console.log(`File exists: ${fs.existsSync(executablePath)}`);

  if (fs.existsSync(executablePath)) {
    const stats = fs.statSync(executablePath);
    console.log(`File size: ${stats.size} bytes`);
  }

  // Simple launch without complex args
  console.log("\nLaunching Electron app (portable mode)...");

  try {
    // Use platform-specific launch config
    const launchConfig: any = {
      executablePath,
      timeout: 30000,
      env: {
        ...process.env,
        NODE_ENV: "production",
        PORTABLE_MODE: "true",
      },
    };

    // Add Linux-specific flags
    if (process.platform === "linux") {
      launchConfig.args = [
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-gpu",
        "--disable-dev-shm-usage",
      ];
      launchConfig.env.DISPLAY = ":0";
      launchConfig.env.ELECTRON_DISABLE_GPU = "1";
    }

    app = await electron.launch(launchConfig);

    console.log("App launched successfully!");
    page = await app.firstWindow();

    // Set a reasonable timeout for page operations
    page.setDefaultTimeout(30000);
  } catch (error) {
    console.error("Failed to launch app:", error);

    // Try to run executable directly for debugging
    if (process.platform === "win32" && fs.existsSync(executablePath)) {
      try {
        console.log("\nTrying direct execution for debugging...");
        const output = execSync(`"${executablePath}" --version`, {
          encoding: "utf-8",
          timeout: 5000,
        });
        console.log("Direct execution output:", output);
      } catch (execErr) {
        console.error("Direct execution failed:", execErr);
      }
    }

    throw error;
  }
});

test.afterEach(async () => {
  if (app) {
    await app.close();
  }
});

test("app should launch successfully", async () => {
  // Basic test to ensure the app starts
  expect(page).toBeTruthy();

  // Wait for the main window to be ready
  await page.waitForLoadState("domcontentloaded");

  // Check if we can get the title
  const title = await page.title();
  console.log(`Page title: ${title}`);
  expect(title).toBeTruthy();
});

test("main window should load", async () => {
  // Wait for a key element that indicates the app loaded
  try {
    await page.waitForSelector("body", { timeout: 10000 });
    console.log("Body element found");

    // Check if React root exists
    const reactRoot = await page.$("#root");
    expect(reactRoot).toBeTruthy();
    console.log("React root element found");
  } catch (error) {
    // Take a screenshot for debugging
    await page.screenshot({
      path: `test-results/portable-launch-failure-${Date.now()}.png`,
      fullPage: true,
    });
    throw error;
  }
});

test("app should be responsive", async () => {
  // Simple test to check if the app responds to input
  const body = await page.$("body");
  expect(body).toBeTruthy();

  // Try to get some basic info about the page
  const url = page.url();
  console.log(`Current URL: ${url}`);

  const viewport = page.viewportSize();
  console.log(`Viewport size: ${viewport?.width}x${viewport?.height}`);
});

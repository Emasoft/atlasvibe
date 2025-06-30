import { ElectronApplication, _electron as electron } from "playwright";
import { test, expect } from "@playwright/test";
import fs from "fs";
import { join } from "path";

/**
 * CI-specific Electron app tests with robust error handling
 */

test.describe("AtlasVibe CI Tests", () => {
  // Only run in CI environments
  test.skip(() => !process.env.CI, "CI-only tests");

  let app: ElectronApplication | null = null;

  test.afterEach(async () => {
    if (app) {
      try {
        await app.close();
      } catch (e) {
        console.error("Error closing app:", e);
      }
      app = null;
    }
  });

  test("Electron app can be launched in CI", async () => {
    const platform = process.platform;
    let executablePath: string;

    // Determine executable path based on platform
    if (platform === "win32") {
      executablePath = join(
        process.cwd(),
        "dist",
        "win-unpacked",
        "atlasvibe.exe",
      );
    } else if (platform === "darwin") {
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
      executablePath = join(
        process.cwd(),
        "dist",
        "linux-unpacked",
        "atlasvibe",
      );
    }

    console.log(`Testing executable: ${executablePath}`);
    console.log(`Platform: ${platform}`);
    console.log(`File exists: ${fs.existsSync(executablePath)}`);

    // Verify executable exists
    expect(fs.existsSync(executablePath)).toBeTruthy();

    // Use the same simple approach that works in the portable test
    console.log("\nLaunching Electron app in CI...");

    // Simple launch configuration that matches the working portable test
    const launchConfig: Parameters<typeof electron.launch>[0] = {
      executablePath,
      timeout: 30000,
      env: {
        ...process.env,
        NODE_ENV: process.env.NODE_ENV || "dev",
      },
    };

    // Only add --no-sandbox in CI on Linux (same as portable test)
    if (platform === "linux") {
      console.log("Running on Linux - adding --no-sandbox flag");
      launchConfig.args = ["--no-sandbox"];
    }

    try {
      app = await electron.launch(launchConfig);
      console.log("✅ Successfully launched Electron app");

      // Basic validation that app started
      const isPackaged = await app.evaluate(
        async ({ app: _app }) => _app.isPackaged,
      );
      expect(isPackaged).toBeTruthy();

      return;
    } catch (error) {
      console.error("❌ Failed to launch Electron app:", error);
      throw error;
    }
  });

  test("App window becomes responsive after launch", async () => {
    // This test depends on the previous test passing
    if (!app) {
      test.skip(true, "App not launched");
      return;
    }

    const firstWindow = await app.firstWindow();
    expect(firstWindow).toBeTruthy();

    // Wait for window to be ready
    await firstWindow.waitForLoadState("domcontentloaded", { timeout: 30000 });

    // Check that we can interact with the window
    const title = await firstWindow.title();
    console.log(`Window title: ${title}`);
    expect(title).toBeTruthy();

    // Try to find body element
    const body = await firstWindow.$("body");
    expect(body).toBeTruthy();
  });
});

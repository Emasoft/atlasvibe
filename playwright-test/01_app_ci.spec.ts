import { ElectronApplication, _electron as electron } from "playwright";
import { test, expect } from "@playwright/test";
import fs from "fs";
import { join } from "path";
import { execSync } from "child_process";

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

    // Try different launch strategies
    const launchStrategies = [
      {
        name: "Minimal",
        config: {
          executablePath,
          timeout: 60000,
        },
      },
      {
        name: "Production mode",
        config: {
          executablePath,
          timeout: 60000,
          env: {
            ...process.env,
            NODE_ENV: "production",
          },
        },
      },
      {
        name: "With basic flags",
        config: {
          executablePath,
          args: ["--no-sandbox"],
          timeout: 60000,
          env: {
            ...process.env,
            NODE_ENV: "production",
          },
        },
      },
      {
        name: "With all CI flags",
        config: {
          executablePath,
          args: [
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
          ],
          timeout: 60000,
          env: {
            ...process.env,
            NODE_ENV: "production",
            ELECTRON_DISABLE_GPU: "1",
          },
        },
      },
    ];

    let lastError: Error | null = null;

    // Try each launch strategy
    for (const strategy of launchStrategies) {
      console.log(`\nTrying launch strategy: ${strategy.name}`);
      try {
        app = await electron.launch(strategy.config);
        console.log(`✅ Successfully launched with strategy: ${strategy.name}`);

        // Basic validation that app started
        const isPackaged = await app.evaluate(
          async ({ app: _app }) => _app.isPackaged,
        );
        expect(isPackaged).toBeTruthy();

        // If we got here, the app launched successfully
        return;
      } catch (error) {
        lastError = error as Error;
        console.error(`❌ Strategy "${strategy.name}" failed:`, error);

        if (app) {
          try {
            await app.close();
          } catch (e) {
            // Ignore close errors
          }
          app = null;
        }
      }
    }

    // If all strategies failed, provide detailed diagnostics
    console.error("\n🔍 All launch strategies failed. Running diagnostics...");

    // Check executable permissions (Linux/macOS)
    if (platform !== "win32") {
      try {
        const stats = fs.statSync(executablePath);
        const mode = (stats.mode & parseInt("777", 8)).toString(8);
        console.log(`File permissions: ${mode}`);

        // Check if executable
        if (!(stats.mode & fs.constants.X_OK)) {
          console.error("❌ File is not executable!");
          execSync(`chmod +x "${executablePath}"`);
          console.log("✅ Made file executable");
        }
      } catch (e) {
        console.error("Error checking permissions:", e);
      }
    }

    // Try direct execution for more error info
    if (platform === "win32") {
      try {
        console.log("\nTrying direct execution with --version...");
        const output = execSync(`"${executablePath}" --version`, {
          encoding: "utf-8",
          timeout: 5000,
        });
        console.log("Version output:", output);
      } catch (e) {
        console.error("Direct execution failed:", e);
      }
    }

    // Linux-specific checks
    if (platform === "linux") {
      try {
        console.log("\nChecking shared library dependencies...");
        const lddOutput = execSync(`ldd "${executablePath}" 2>&1 || true`, {
          encoding: "utf-8",
        });
        const missingLibs = lddOutput
          .split("\n")
          .filter((line) => line.includes("not found"));
        if (missingLibs.length > 0) {
          console.error("❌ Missing libraries:");
          missingLibs.forEach((lib) => console.error(`  - ${lib}`));
        } else {
          console.log("✅ All shared libraries found");
        }
      } catch (e) {
        console.error("Error checking libraries:", e);
      }
    }

    // Throw the last error with context
    throw new Error(
      `Failed to launch Electron app after trying ${launchStrategies.length} strategies. ` +
        `Last error: ${lastError?.message || "Unknown error"}`,
    );
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

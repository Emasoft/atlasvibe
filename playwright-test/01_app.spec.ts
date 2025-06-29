/*
 * Copyright (c) 2024 Emasoft
 *
 * This file is part of AtlasVibe, which is based on Flojoy Studio
 * Original Copyright (c) 2023-2024 Flojoy
 *
 * SPDX-License-Identifier: MIT
 * See the LICENSE file for details.
 */

import { ElectronApplication, _electron as electron } from "playwright";
import { test, expect } from "@playwright/test";
import fs from "fs";
import { join } from "path";
import { execSync } from "child_process";
import {
  STARTUP_TIMEOUT,
  getExecutablePath,
  mockDialogMessage,
  writeLogFile,
} from "./utils";
const { productName, version } = JSON.parse(
  fs.readFileSync(join(process.cwd(), "package.json"), { encoding: "utf-8" }),
);

test.describe(`${productName} startup test`, () => {
  let app: ElectronApplication;
  test.beforeAll(async () => {
    const executablePath = getExecutablePath();
    console.log(`Executable path: ${executablePath}`);
    console.log(`File exists: ${fs.existsSync(executablePath)}`);

    if (fs.existsSync(executablePath)) {
      // Check file permissions
      try {
        const stats = fs.statSync(executablePath);
        console.log(
          `File permissions: ${(stats.mode & parseInt("777", 8)).toString(8)}`,
        );
        console.log(`Is file: ${stats.isFile()}`);
        console.log(`File size: ${stats.size} bytes`);
      } catch (e) {
        console.error(`Error checking file stats: ${e}`);
      }

      // Try to execute the file directly to see what error we get
      if (process.platform === "linux" || process.platform === "win32") {
        try {
          if (process.platform === "linux") {
            // First try just getting version or help
            const lddOutput = execSync(`ldd "${executablePath}" 2>&1 || true`, {
              encoding: "utf-8",
            });
            console.log(`ldd output:\n${lddOutput}`);
          }

          // Try running the app directly to see what happens
          console.log(
            "\nTrying to run the app directly to check for errors...",
          );
          try {
            // Run with --version or --help to see if it starts at all
            const helpOutput = execSync(
              `"${executablePath}" --help 2>&1 || true`,
              {
                encoding: "utf-8",
                timeout: 5000,
              },
            );
            console.log(`Help output: ${helpOutput}`);
          } catch (helpError) {
            console.error(`Error running --help: ${helpError}`);
          }

          // Check if there's a crash log
          try {
            const crashCheck = execSync(
              `"${executablePath}" --no-sandbox 2>&1 || echo "Exit code: $?"`,
              {
                encoding: "utf-8",
                timeout: 5000,
                env: { ...process.env, ELECTRON_ENABLE_LOGGING: "1" },
              },
            );
            console.log(`Direct run output: ${crashCheck}`);
          } catch (runError) {
            console.error(`Error running directly: ${runError}`);
          }
        } catch (e) {
          console.error(`Error during debug checks: ${e}`);
        }
      }
    }

    if (!fs.existsSync(executablePath)) {
      // List contents of dist directory to help debug
      const distPath = join(process.cwd(), "dist");
      if (fs.existsSync(distPath)) {
        console.log(`Contents of dist directory:`);
        const dirs = fs.readdirSync(distPath);
        dirs.forEach((dir) => {
          console.log(`  - ${dir}`);
          const subdirPath = join(distPath, dir);
          if (fs.statSync(subdirPath).isDirectory() && dir.includes("linux")) {
            console.log(`    Contents of ${dir}:`);
            const files = fs.readdirSync(subdirPath);
            files.forEach((file) => {
              console.log(`      - ${file}`);
            });
          }
        });
      }
    }

    // Use the same simple approach that works in the portable test
    console.log("\nLaunching Electron app...");

    // Simple launch configuration that matches the working portable test
    const launchConfig: Parameters<typeof electron.launch>[0] = {
      executablePath,
      timeout: 30000,
      env: {
        ...process.env,
        NODE_ENV: "production",
      },
    };

    // Only add --no-sandbox in CI on Linux (same as portable test)
    if (process.env.CI && process.platform === "linux") {
      console.log("Running in CI on Linux - adding --no-sandbox flag");
      launchConfig.args = ["--no-sandbox"];
    }

    try {
      app = await electron.launch(launchConfig);
      console.log("✅ Successfully launched Electron app");
    } catch (error) {
      console.error("❌ Failed to launch Electron app:", error);
      throw error;
    }
    await mockDialogMessage(app);
  }, 60000); // 1 minute timeout for setup

  test.afterAll(async () => {
    if (app) {
      await writeLogFile(app, `atlasvibe-startup-test`);
      await app.close();
    }
  });

  test("Check if app is packaged", async () => {
    const isPackaged = await app.evaluate(async ({ app: _app }) => {
      return _app.isPackaged;
    });
    expect(isPackaged).toBe(true);
  });

  test(`Check if title matches product name: ${productName}`, async () => {
    const appName = await app.evaluate(async ({ app: _app }) => {
      return _app.getName();
    });
    // The app explicitly sets its name to "Atlasvibe Studio" in src/main/index.ts
    expect(appName).toBe("Atlasvibe Studio");
  });

  test(`Check if version matches package.json version: ${version}`, async () => {
    const appVersion = await app.evaluate(async ({ app: _app }) => {
      return _app.getVersion();
    });
    expect(appVersion).toEqual(version);
  });

  test("App should be loaded correctly.", async () => {
    test.setTimeout(STARTUP_TIMEOUT);
    const window = await app.firstWindow({ timeout: STARTUP_TIMEOUT / 2 });
    await window.waitForLoadState("domcontentloaded");
    const title = await window.$("title");
    // The app uses "Atlasvibe Studio" as its title
    expect(await title?.innerText()).toContain("Atlasvibe Studio");
    const welcomeText = `Welcome to Atlasvibe Studio V${version}`;
    await window.getByText(welcomeText).innerText({ timeout: STARTUP_TIMEOUT });
  });
});

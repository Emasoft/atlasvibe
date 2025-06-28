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

    // Try launching with the minimal configuration that works in CI
    console.log("\nAttempting to launch Electron app...");

    // Use the minimal launch strategy that has been proven to work
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

    // Add Linux-specific strategies
    if (process.platform === "linux") {
      launchStrategies.push({
        name: "Linux with display flags",
        config: {
          executablePath,
          args: [
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-gpu",
            "--disable-gpu-sandbox",
            "--disable-software-rasterizer",
            "--disable-dev-shm-usage",
          ],
          timeout: 60000,
          env: {
            ...process.env,
            DISPLAY: ":0",
            NODE_ENV: "production",
            ELECTRON_DISABLE_GPU: "1",
            ELECTRON_NO_SANDBOX: "1",
          },
        },
      });
    }

    let lastError: Error | null = null;
    let launched = false;

    // Try each launch strategy
    for (const strategy of launchStrategies) {
      console.log(`Trying launch strategy: ${strategy.name}`);
      try {
        app = await electron.launch(strategy.config);
        console.log(`✅ Successfully launched with strategy: ${strategy.name}`);
        launched = true;
        break;
      } catch (error) {
        lastError = error as Error;
        console.error(`❌ Strategy "${strategy.name}" failed:`, error);
      }
    }

    if (!launched) {
      console.error("Failed to launch Electron app with any strategy");

      // Additional debugging for Windows
      if (process.platform === "win32" && fs.existsSync(executablePath)) {
        try {
          console.log("\nChecking if executable responds to --version...");
          const versionOutput = execSync(`"${executablePath}" --version 2>&1`, {
            encoding: "utf-8",
            timeout: 5000,
          }).trim();
          console.log("Version output:", versionOutput);
        } catch (versionErr) {
          console.error("Version check failed:", versionErr);
        }
      }

      throw lastError || new Error("Failed to launch app with any strategy");
    }
    await mockDialogMessage(app);
  }, 120000); // Increase timeout to 2 minutes for Windows

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
    expect(appName).toBe(productName);
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
    expect(await title?.innerText()).toContain(productName);
    const welcomeText = `Welcome to Atlasvibe Studio V${version}`;
    await window.getByText(welcomeText).innerText({ timeout: STARTUP_TIMEOUT });
  });
});

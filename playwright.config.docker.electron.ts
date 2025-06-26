import { defineConfig } from "@playwright/test";

/**
 * Playwright configuration for Electron tests in Docker
 * Skips tests that require full Electron app and focuses on backend/API tests
 */
export default defineConfig({
  workers: 1,
  testDir: "./playwright-test",
  // Only run Docker-safe tests
  testMatch: [
    "**/00_headless_check.spec.docker.ts",
    "**/00_docker_backend.spec.ts",
    "**/00_api_smoke.spec.ts",
  ],
  timeout: 120000, // 2 minutes timeout per test

  outputDir: "./test-results",

  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,

  reporter: [
    ["list"],
    ["json", { outputFile: "./test-results/results.json" }],
    ["html", { outputFolder: "./playwright-report", open: "never" }],
  ],

  use: {
    headless: true,

    launchOptions: {
      args: [
        "--disable-gpu",
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
      ],
    },

    viewport: { width: 1280, height: 720 },
    ignoreHTTPSErrors: true,

    trace: "retain-on-failure",
    video: "retain-on-failure",
    screenshot: "only-on-failure",
  },

  projects: [
    {
      name: "chromium-docker",
      use: {
        ...require("@playwright/test").devices["Desktop Chrome"],
        // Override any device-specific settings that might cause issues
        viewport: { width: 1280, height: 720 },
        hasTouch: false,
        isMobile: false,
      },
    },
  ],

  maxFailures: 10,
});

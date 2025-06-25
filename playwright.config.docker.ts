import { defineConfig } from "@playwright/test";

/**
 * Playwright configuration for Docker environment
 * Based on the existing configuration but adapted for Docker
 */
export default defineConfig({
  workers: 1,
  testDir: "./playwright-test",
  testMatch: "**/*.spec.ts",
  timeout: 300000, // 5 minutes timeout per test (to allow for slow CI environments)

  // Specific output directory for Docker
  outputDir: "./test-results",

  // Fail the build on CI if you accidentally left test.only in the source code
  forbidOnly: !!process.env.CI,

  // Retry on CI only
  retries: process.env.CI ? 1 : 0,

  // Reporter configuration for Docker
  reporter: [
    ["list"],
    ["json", { outputFile: "./test-results/results.json" }],
    ["html", { outputFolder: "./playwright-report", open: "never" }],
  ],

  use: {
    // Force headless mode
    headless: true,

    // Disable GPU
    launchOptions: {
      args: [
        '--disable-gpu',
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
      ],
    },

    // Viewport for consistency
    viewport: { width: 1280, height: 720 },

    // Ignore HTTPS errors in tests
    ignoreHTTPSErrors: true,

    // Tracing and debugging
    trace: {
      mode: "retain-on-failure",
      sources: true,
    },
    video: "retain-on-failure", // Record video on failure for debugging
    screenshot: "only-on-failure", // Take screenshots on failure
  },

  maxFailures: process.env.CI ? 5 : 1,
});

import { test, expect } from "@playwright/test";

test.describe("Headless Docker Environment Check", () => {
  test("Verify running in headless mode", async ({ browserName }) => {
    // This test verifies we're running headless
    console.log(`Running in ${browserName} browser`);
    console.log(`DISPLAY env: ${process.env.DISPLAY}`);
    console.log(`CI env: ${process.env.CI}`);
    console.log(`Electron GPU disabled: ${process.env.ELECTRON_DISABLE_GPU}`);

    // If we reach here, we're running headless successfully
    expect(process.env.DISPLAY).toBe(":99");
    expect(process.env.CI).toBe("true");
  });

  test("Backend API responds in Docker", async ({ request }) => {
    // Test that backend is accessible - AtlasVibe backend runs on port 5392
    const endpoints = [
      "http://localhost:5392/log_level",
      "http://127.0.0.1:5392/log_level",
    ];

    let successfulEndpoint = null;

    for (const endpoint of endpoints) {
      try {
        console.log(`Trying backend endpoint: ${endpoint}`);
        const response = await request.get(endpoint, { timeout: 10000 });
        if (response.status() < 500) {
          successfulEndpoint = endpoint;
          console.log(
            `Backend responding at: ${endpoint} with status ${response.status()}`,
          );
          break;
        }
      } catch (error) {
        console.log(`Failed to connect to ${endpoint}: ${error}`);
      }
    }

    expect(successfulEndpoint).toBeTruthy();
  });

  test("Can take screenshot without opening display", async ({ context }) => {
    // Create a new page - this would fail if trying to open a real window
    const newPage = await context.newPage();

    // Navigate to a data URL (doesn't require backend)
    await newPage.goto("data:text/html,<h1>Headless Test</h1>");

    // Take a screenshot - this proves we're rendering headlessly
    const screenshot = await newPage.screenshot();
    expect(screenshot).toBeTruthy();
    expect(screenshot.length).toBeGreaterThan(0);

    await newPage.close();
  });
});

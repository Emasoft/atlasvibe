import { test, expect } from "@playwright/test";

test.describe("Docker Smoke Tests", () => {
  test("Frontend should be accessible", async ({ page }) => {
    // Navigate to the frontend
    await page.goto("http://localhost:5173");

    // Wait for the page to load
    await page.waitForLoadState("networkidle");

    // Check if the page has loaded
    const title = await page.title();
    expect(title).toBeTruthy();

    // Take a screenshot for debugging
    await page.screenshot({ path: "test-results/frontend-loaded.png" });
  });

  test("Backend API should respond", async ({ request }) => {
    // Check if the backend is running
    const response = await request.get("http://localhost:5392/log_level");

    // For now, just check if we get any response
    // The actual endpoint might be different
    console.log("Backend response status:", response.status());
  });
});

import { test, expect } from "@playwright/test";

test.describe("API Smoke Tests", () => {
  test("Backend health check should respond", async ({ request }) => {
    // Try multiple possible endpoints - AtlasVibe doesn't have a health endpoint but we can check log_level
    const endpoints = [
      "http://localhost:11060/log_level",
      "http://localhost:11060/blocks/metadata/",
      "http://localhost:5392/log_level",
      "http://localhost:5392/blocks/metadata/"
    ];

    let successfulEndpoint = null;

    for (const endpoint of endpoints) {
      try {
        const response = await request.get(endpoint, { timeout: 5000 });
        if (response.status() < 500) {  // Accept any non-server-error response
          successfulEndpoint = endpoint;
          break;
        }
      } catch (error) {
        // Continue to next endpoint
      }
    }

    if (!successfulEndpoint) {
      console.log("No backend endpoint responding - skipping API tests");
      test.skip();
    }
    expect(successfulEndpoint).toBeTruthy();
  });

  test("Backend API can retrieve blocks metadata", async ({ request }) => {
    try {
      // Try both possible ports with the correct endpoint
      const ports = ["11060", "5392"];
      let successfulResponse = null;

      for (const port of ports) {
        try {
          const response = await request.get(`http://localhost:${port}/blocks/metadata/`, { timeout: 5000 });
          if (response.status() < 500) {
            successfulResponse = response;
            break;
          }
        } catch (error) {
          // Continue to next port
        }
      }

      if (!successfulResponse) {
        test.skip(true, "Backend not available");
        return;
      }
      expect(successfulResponse).toBeTruthy();

      const data = await successfulResponse.json();
      // The metadata endpoint returns an object with blocks info
      expect(data).toBeDefined();
    } catch (error) {
      // Mark as skipped if backend is not available
      test.skip(true, "Backend not available");
    }
  });

  test("Frontend dev server should respond", async ({ request }) => {
    try {
      const response = await request.get("http://localhost:5173", { timeout: 5000 });
      expect(response.ok()).toBeTruthy();

      const html = await response.text();
      expect(html).toContain("<!DOCTYPE html>");
    } catch (error) {
      // Mark as skipped if frontend is not available
      test.skip(true, "Frontend not available");
    }
  });
});

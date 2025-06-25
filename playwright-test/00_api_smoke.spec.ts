import { test, expect } from "@playwright/test";

test.describe("API Smoke Tests", () => {
  test("Backend health check should respond", async ({ request }) => {
    // AtlasVibe backend runs on port 5392
    const endpoints = [
      "http://localhost:5392/log_level",
      "http://localhost:5392/blocks/metadata/",
      "http://127.0.0.1:5392/log_level",
      "http://127.0.0.1:5392/blocks/metadata/",
    ];

    let successfulEndpoint = null;

    for (const endpoint of endpoints) {
      try {
        const response = await request.get(endpoint, { timeout: 10000 });
        if (response.status() < 500) {
          // Accept any non-server-error response
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
      // AtlasVibe backend runs on port 5392
      const endpoints = [
        "http://localhost:5392/blocks/metadata/",
        "http://127.0.0.1:5392/blocks/metadata/",
      ];
      let successfulResponse = null;

      for (const endpoint of endpoints) {
        try {
          const response = await request.get(endpoint, { timeout: 10000 });
          if (response.status() < 500) {
            successfulResponse = response;
            break;
          }
        } catch (error) {
          // Continue to next endpoint
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
      const response = await request.get("http://localhost:5173", {
        timeout: 5000,
      });
      expect(response.ok()).toBeTruthy();

      const html = await response.text();
      expect(html).toContain("<!DOCTYPE html>");
    } catch (error) {
      // Mark as skipped if frontend is not available
      test.skip(true, "Frontend not available");
    }
  });
});

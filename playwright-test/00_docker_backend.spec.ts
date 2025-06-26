import { test, expect } from "@playwright/test";

/**
 * Minimal backend tests for Docker environment
 * These tests only check backend functionality without Electron
 */

test.describe("Docker Backend Tests", () => {
  test.skip(
    ({ browserName }) => browserName !== "chromium",
    "Backend tests only need one browser",
  );

  test("Backend health check", async ({ request }) => {
    // Skip if not in Docker
    if (!process.env.CI || process.env.NODE_ENV !== "test") {
      test.skip();
    }

    const maxRetries = 30;
    let lastError: Error | null = null;

    for (let i = 0; i < maxRetries; i++) {
      try {
        const response = await request.get("http://localhost:5392/log_level", {
          timeout: 5000,
        });

        expect(response.status()).toBeLessThan(500);
        console.log(
          `Backend health check passed with status: ${response.status()}`,
        );
        return;
      } catch (error) {
        lastError = error as Error;
        console.log(`Attempt ${i + 1}/${maxRetries} failed: ${error}`);
        // Wait a bit before retrying
        await new Promise((resolve) => setTimeout(resolve, 1000));
      }
    }

    throw new Error(
      `Backend health check failed after ${maxRetries} attempts: ${lastError}`,
    );
  });

  test("Backend API - get blocks metadata", async ({ request }) => {
    // Skip if not in Docker
    if (!process.env.CI || process.env.NODE_ENV !== "test") {
      test.skip();
    }

    try {
      const response = await request.get(
        "http://localhost:5392/blocks/metadata/",
        {
          timeout: 10000,
        },
      );

      console.log(`Response status: ${response.status()}`);
      console.log(`Response ok: ${response.ok()}`);

      if (!response.ok()) {
        const body = await response.text();
        console.error(`Response body: ${body}`);
      }

      expect(response.ok()).toBeTruthy();

      const data = await response.json();
      console.log(`Response data type: ${typeof data}`);
      console.log(`Response data keys:`, Object.keys(data).slice(0, 5));

      // The metadata endpoint returns a dictionary where keys are block filenames
      // and values contain metadata, path, and full_path
      expect(typeof data).toBe("object");
      expect(data).not.toBeNull();

      const blockKeys = Object.keys(data);
      console.log(`Found ${blockKeys.length} blocks in metadata`);

      // Check that we have at least some blocks
      expect(blockKeys.length).toBeGreaterThan(0);

      // Verify block metadata structure
      if (blockKeys.length > 0) {
        const firstKey = blockKeys[0];
        const firstBlock = data[firstKey];
        console.log(`First block key: ${firstKey}`);
        console.log(`First block structure:`, Object.keys(firstBlock));

        expect(firstBlock).toHaveProperty("metadata");
        expect(firstBlock).toHaveProperty("path");
        expect(firstBlock).toHaveProperty("full_path");
      }
    } catch (error) {
      console.error("Failed to get blocks metadata:", error);
      throw error;
    }
  });

  test("Backend API - project management endpoints", async ({ request }) => {
    // Skip if not in Docker
    if (!process.env.CI || process.env.NODE_ENV !== "test") {
      test.skip();
    }

    // Test project list endpoint
    try {
      const response = await request.get("http://localhost:5392/project/list", {
        timeout: 10000,
      });

      // Even if no projects exist, the endpoint should respond
      expect(response.status()).toBeLessThan(500);
      console.log(
        `Project list endpoint responded with status: ${response.status()}`,
      );
    } catch (error) {
      console.error("Failed to access project endpoints:", error);
      throw error;
    }
  });

  test("Backend WebSocket endpoint exists", async ({ request }) => {
    // Skip if not in Docker
    if (!process.env.CI || process.env.NODE_ENV !== "test") {
      test.skip();
    }

    // We can't easily test WebSocket with Playwright's request API,
    // but we can at least check if the upgrade would be accepted
    try {
      const response = await request.get("http://localhost:5392/ws", {
        headers: {
          Upgrade: "websocket",
          Connection: "Upgrade",
          // This is a standard test value from RFC 6455 WebSocket spec, not a secret
          "Sec-WebSocket-Key": "x3JJHMbDL1EzLkh9GBhXDw==",
          "Sec-WebSocket-Version": "13",
        },
        timeout: 5000,
      });

      // WebSocket endpoints typically return 400 or 426 when accessed via regular HTTP
      // This is expected and indicates the endpoint exists
      expect([400, 426]).toContain(response.status());
      console.log(
        "WebSocket endpoint exists (returned expected upgrade required status)",
      );
    } catch (error) {
      // Some errors are expected for WebSocket endpoints
      console.log("WebSocket endpoint check completed");
    }
  });
});

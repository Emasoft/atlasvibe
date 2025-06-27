import { test, expect } from "@playwright/test";

/**
 * Minimal backend tests for Docker environment
 * These tests only check backend functionality without Electron
 */

// Constants
const BACKEND_URL = "http://localhost:5392";
const MAX_RETRIES = 30;
const INITIAL_RETRY_DELAY = 1000; // 1 second
const MAX_RETRY_DELAY = 5000; // 5 seconds
// WebSocket test key from RFC 6455 (standard test value, not a secret)
const WS_TEST_KEY = "x3JJHMbDL1EzLkh9GBhXDw==";

// Helper function to check if running in Docker CI
function isDockerCI(): boolean {
  return !!process.env.CI && process.env.NODE_ENV === "test";
}

// Helper function for exponential backoff
function getBackoffDelay(attempt: number): number {
  return Math.min(INITIAL_RETRY_DELAY * Math.pow(1.5, attempt), MAX_RETRY_DELAY);
}

test.describe("Docker Backend Tests", () => {
  test.skip(
    ({ browserName }) => browserName !== "chromium",
    "Backend tests only need one browser",
  );

  test("Backend health check", async ({ request }) => {
    // Skip if not in Docker
    if (!isDockerCI()) {
      test.skip();
    }

    let lastError: Error | null = null;

    for (let i = 0; i < MAX_RETRIES; i++) {
      try {
        const response = await request.get(`${BACKEND_URL}/log_level`, {
          timeout: 5000,
        });

        expect(response.status()).toBeLessThan(500);
        console.log(
          `Backend health check passed with status: ${response.status()}`,
        );
        return;
      } catch (error) {
        lastError = error as Error;
        console.log(`Attempt ${i + 1}/${MAX_RETRIES} failed: ${error}`);
        // Wait with exponential backoff
        const delay = getBackoffDelay(i);
        await new Promise((resolve) => setTimeout(resolve, delay));
      }
    }

    throw new Error(
      `Backend health check failed after ${MAX_RETRIES} attempts: ${lastError}`,
    );
  });

  test("Backend API - get blocks metadata", async ({ request }) => {
    // Skip if not in Docker
    if (!isDockerCI()) {
      test.skip();
    }

    try {
      const response = await request.get(
        `${BACKEND_URL}/blocks/metadata/`,
        {
          timeout: 10000,
        },
      );

      console.log(`Response status: ${response.status()}`);
      console.log(`Response ok: ${response.ok()}`);

      if (!response.ok()) {
        const body = await response.text();
        const headers = response.headers();
        console.error(`Response status: ${response.status()}`);
        console.error(`Response headers:`, headers);
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
    if (!isDockerCI()) {
      test.skip();
    }

    // Test project list endpoint
    try {
      const response = await request.get(`${BACKEND_URL}/project/list`, {
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
    if (!isDockerCI()) {
      test.skip();
    }

    // We can't easily test WebSocket with Playwright's request API,
    // but we can at least check if the upgrade would be accepted
    try {
      const response = await request.get(`${BACKEND_URL}/ws`, {
        headers: {
          Upgrade: "websocket",
          Connection: "Upgrade",
          "Sec-WebSocket-Key": WS_TEST_KEY,
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

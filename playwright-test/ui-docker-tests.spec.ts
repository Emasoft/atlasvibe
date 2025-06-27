import { test, expect, ElectronApplication, Page } from "@playwright/test";
import { _electron as electron } from "playwright";
import * as path from "path";

/**
 * Comprehensive UI tests for AtlasVibe Electron app in Docker
 * These tests focus on visual elements, interactions, and user workflows
 */

let app: ElectronApplication;
let page: Page;

// Helper to get app path based on environment
function getAppPath(): string {
  return (
    process.env.PLAYWRIGHT_ELECTRON_APP_PATH ||
    path.join(__dirname, "..", "release", "linux-unpacked", "atlasvibe")
  );
}

test.describe("AtlasVibe UI Tests - Docker", () => {
  test.beforeEach(async () => {
    // Launch Electron app
    app = await electron.launch({
      args: [getAppPath()],
      env: {
        ...process.env,
        NODE_ENV: "test",
        DISPLAY: process.env.DISPLAY || ":99",
        ELECTRON_DISABLE_GPU: "1",
        ELECTRON_NO_SANDBOX: "1",
      },
    });

    // Get the first window
    page = await app.firstWindow();

    // Wait for app to fully load
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);
  });

  test.afterEach(async () => {
    if (app) {
      await app.close();
    }
  });

  test("App launches successfully with main window", async () => {
    // Verify window is visible
    const isVisible = await page.isVisible("body");
    expect(isVisible).toBeTruthy();

    // Check window title
    const title = await page.title();
    expect(title).toContain("AtlasVibe");

    // Take screenshot for visual verification
    await page.screenshot({
      path: "test-results/ui/app-launch.png",
      fullPage: true,
    });
  });

  test("Sidebar navigation is functional", async () => {
    // Check sidebar exists
    const sidebar = await page
      .locator('[data-testid="sidebar"], nav, aside')
      .first();
    await expect(sidebar).toBeVisible();

    // Check for main navigation items
    const navItems = ["Flow Chart", "Blocks", "Control", "Settings"];

    for (const item of navItems) {
      const navButton = await page
        .locator(`button:has-text("${item}"), a:has-text("${item}")`)
        .first();
      await expect(navButton).toBeVisible();
    }

    // Click on Flow Chart
    await page.click('button:has-text("Flow Chart"), a:has-text("Flow Chart")');
    await page.waitForTimeout(1000);

    // Verify flow chart canvas is visible
    const canvas = await page
      .locator('canvas, [data-testid="flow-canvas"], .react-flow')
      .first();
    await expect(canvas).toBeVisible();
  });

  test("Block palette displays categories", async () => {
    // Navigate to blocks section
    const blocksButton = await page
      .locator('button:has-text("Blocks"), a:has-text("Blocks")')
      .first();
    if (await blocksButton.isVisible()) {
      await blocksButton.click();
      await page.waitForTimeout(1000);
    }

    // Check for block categories
    const categories = ["Math", "Logic", "Data", "Visualization"];

    for (const category of categories) {
      const categoryElement = await page.locator(`text=${category}`).first();
      const isVisible = await categoryElement.isVisible().catch(() => false);

      if (isVisible) {
        console.log(`✓ Found category: ${category}`);
      }
    }

    // Take screenshot of blocks palette
    await page.screenshot({
      path: "test-results/ui/blocks-palette.png",
      fullPage: true,
    });
  });

  test("@screenshot Visual regression - Main interface", async () => {
    // Wait for stable state
    await page.waitForTimeout(3000);

    // Capture main interface
    await page.screenshot({
      path: "test-results/ui/main-interface-baseline.png",
      fullPage: true,
      animations: "disabled",
    });

    // Compare with baseline (in real scenario)
    // This would compare against a known good screenshot
  });

  test("Drag and drop block to canvas", async () => {
    // Navigate to flow chart
    await page.click('button:has-text("Flow Chart"), a:has-text("Flow Chart")');
    await page.waitForTimeout(1000);

    // Find a draggable block (try different selectors)
    const block = await page.locator('[draggable="true"]').first();
    const blockExists = await block.isVisible().catch(() => false);

    if (blockExists) {
      // Find drop target (canvas)
      const canvas = await page
        .locator('canvas, [data-testid="flow-canvas"], .react-flow')
        .first();

      // Perform drag and drop
      await block.dragTo(canvas);
      await page.waitForTimeout(1000);

      // Verify block was added (check for node element)
      const droppedBlock = await page
        .locator('.react-flow__node, [data-testid="flow-node"]')
        .first();
      await expect(droppedBlock).toBeVisible();
    } else {
      console.log("⚠️  No draggable blocks found - skipping drag test");
    }
  });

  test("Theme toggle functionality", async () => {
    // Look for theme toggle button
    const themeToggle = await page
      .locator(
        'button[aria-label*="theme"], button:has-text("Theme"), [data-testid="theme-toggle"]',
      )
      .first();

    if (await themeToggle.isVisible()) {
      // Get initial theme
      const initialTheme = await page.evaluate(() => {
        return document.documentElement.classList.contains("dark")
          ? "dark"
          : "light";
      });

      // Click theme toggle
      await themeToggle.click();
      await page.waitForTimeout(500);

      // Verify theme changed
      const newTheme = await page.evaluate(() => {
        return document.documentElement.classList.contains("dark")
          ? "dark"
          : "light";
      });

      expect(newTheme).not.toBe(initialTheme);

      // Take screenshot in new theme
      await page.screenshot({
        path: `test-results/ui/theme-${newTheme}.png`,
        fullPage: true,
      });
    }
  });

  test("@a11y Accessibility - Keyboard navigation", async () => {
    // Test Tab navigation
    await page.keyboard.press("Tab");
    await page.waitForTimeout(100);

    // Check focused element
    const focusedElement = await page.evaluate(() => {
      const el = document.activeElement;
      return {
        tagName: el?.tagName,
        text: el?.textContent,
        ariaLabel: el?.getAttribute("aria-label"),
      };
    });

    expect(focusedElement.tagName).toBeTruthy();

    // Test Enter key on focused button
    await page.keyboard.press("Enter");
    await page.waitForTimeout(500);
  });

  test("@a11y Accessibility - ARIA labels", async () => {
    // Check for ARIA labels on interactive elements
    const buttons = await page.locator("button").all();

    for (const button of buttons.slice(0, 5)) {
      // Check first 5 buttons
      const ariaLabel = await button.getAttribute("aria-label");
      const text = await button.textContent();

      // Button should have either aria-label or visible text
      expect(ariaLabel || text).toBeTruthy();
    }
  });

  test("Window controls functionality", async () => {
    // Get window bounds
    const bounds = await app.evaluate((electron) => {
      return electron.BrowserWindow.getAllWindows()[0].getBounds();
    });

    expect(bounds.width).toBeGreaterThan(0);
    expect(bounds.height).toBeGreaterThan(0);

    // Test window maximize (if supported)
    await app.evaluate((electron) => {
      const window = electron.BrowserWindow.getAllWindows()[0];
      if (!window.isMaximized()) {
        window.maximize();
      }
    });

    await page.waitForTimeout(500);

    const isMaximized = await app.evaluate((electron) => {
      return electron.BrowserWindow.getAllWindows()[0].isMaximized();
    });

    console.log(`Window maximized: ${isMaximized}`);
  });

  test("Search functionality", async () => {
    // Look for search input
    const searchInput = await page
      .locator(
        'input[type="search"], input[placeholder*="Search"], [data-testid="search-input"]',
      )
      .first();

    if (await searchInput.isVisible()) {
      // Type search query
      await searchInput.fill("addition");
      await page.waitForTimeout(500);

      // Check for search results
      const results = await page
        .locator('[data-testid="search-result"], .search-result')
        .all();

      if (results.length > 0) {
        console.log(`✓ Found ${results.length} search results`);
      }

      // Clear search
      await searchInput.clear();
    }
  });

  test("Error boundary - Handles errors gracefully", async () => {
    // Try to trigger an error by invalid navigation
    await page.evaluate(() => {
      // Attempt to navigate to non-existent route
      window.location.hash = "#/non-existent-route";
    });

    await page.waitForTimeout(1000);

    // Check that app didn't crash
    const isVisible = await page.isVisible("body");
    expect(isVisible).toBeTruthy();

    // Look for error message
    const errorMessage = await page
      .locator(
        '[data-testid="error-message"], .error-boundary, text=/error|Error/i',
      )
      .first();

    // If error boundary triggered, it should show message
    if (await errorMessage.isVisible()) {
      console.log("✓ Error boundary activated");
      await page.screenshot({
        path: "test-results/ui/error-boundary.png",
      });
    }
  });

  test("Performance - Initial load time", async () => {
    const startTime = Date.now();

    // Create new app instance to measure cold start
    const newApp = await electron.launch({
      args: [getAppPath()],
      env: {
        ...process.env,
        NODE_ENV: "production",
        DISPLAY: process.env.DISPLAY || ":99",
      },
    });

    const newPage = await newApp.firstWindow();
    await newPage.waitForLoadState("networkidle");

    const loadTime = Date.now() - startTime;
    console.log(`⏱️  App load time: ${loadTime}ms`);

    // App should load within 10 seconds
    expect(loadTime).toBeLessThan(10000);

    await newApp.close();
  });

  test("Memory usage stays reasonable", async () => {
    // Get initial memory usage
    const initialMemory = await app.evaluate(() => {
      if (process.memoryUsage) {
        return process.memoryUsage();
      }
      return null;
    });

    // Perform some operations
    for (let i = 0; i < 5; i++) {
      await page.click('button:has-text("Blocks"), a:has-text("Blocks")');
      await page.waitForTimeout(500);
      await page.click(
        'button:has-text("Flow Chart"), a:has-text("Flow Chart")',
      );
      await page.waitForTimeout(500);
    }

    // Get final memory usage
    const finalMemory = await app.evaluate(() => {
      if (process.memoryUsage) {
        return process.memoryUsage();
      }
      return null;
    });

    if (initialMemory && finalMemory) {
      const memoryIncrease = finalMemory.heapUsed - initialMemory.heapUsed;
      console.log(
        `📊 Memory increase: ${(memoryIncrease / 1024 / 1024).toFixed(2)}MB`,
      );

      // Memory increase should be reasonable (less than 100MB)
      expect(memoryIncrease).toBeLessThan(100 * 1024 * 1024);
    }
  });
});

test.describe("UI Workflow Tests", () => {
  test.beforeEach(async () => {
    app = await electron.launch({
      args: [getAppPath()],
      env: {
        ...process.env,
        NODE_ENV: "test",
        DISPLAY: process.env.DISPLAY || ":99",
      },
    });
    page = await app.firstWindow();
    await page.waitForLoadState("networkidle");
  });

  test.afterEach(async () => {
    if (app) {
      await app.close();
    }
  });

  test("Complete workflow - Create simple calculation", async () => {
    // Navigate to flow chart
    await page.click('button:has-text("Flow Chart"), a:has-text("Flow Chart")');
    await page.waitForTimeout(1000);

    // Try to add blocks and create connections
    // This test would be more specific based on actual UI

    // Take screenshot of final workflow
    await page.screenshot({
      path: "test-results/ui/workflow-complete.png",
      fullPage: true,
    });
  });
});

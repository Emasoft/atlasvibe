/*
 * Copyright (c) 2024 Emasoft
 *
 * This file is part of AtlasVibe, which is based on Flojoy Studio
 * Original Copyright (c) 2023-2024 Flojoy
 *
 * SPDX-License-Identifier: MIT
 * See the LICENSE file for details.
 */

import { defineConfig } from "@playwright/test";

export default defineConfig({
  workers: 1,
  testDir: "./playwright-test",
  testMatch: "**/*.spec.ts",
  timeout: 300000, // 5 minutes timeout per test (to allow for slow CI environments)
  use: {
    trace: {
      mode: "retain-on-failure",
      sources: true,
    },
    video: "retain-on-failure", // Record video on failure for debugging
    screenshot: "only-on-failure", // Take screenshots on failure
  },
  maxFailures: 1,
  reporter: [["list"], ["html", { open: "never" }]],
});

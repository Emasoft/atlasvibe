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
  use: {
    trace: {
      mode: "retain-on-failure",
      sources: true,
    },
  },
  maxFailures: 1,
});

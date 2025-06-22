/*
 * Copyright (c) 2024 Emasoft
 *
 * This file is part of AtlasVibe, which is based on Flojoy Studio
 * Original Copyright (c) 2023-2024 Flojoy
 *
 * SPDX-License-Identifier: MIT
 * See the LICENSE file for details.
 */

import { app } from "electron";
import { join } from "node:path";

// Without ASAR, the directory structure is different
export const WORKING_DIR = app.isPackaged
  ? join(app.getAppPath(), "..") // Go up from app directory when packaged
  : join(__dirname, "../../"); // Development mode

export const DIST_ELECTRON = join(WORKING_DIR, "out");
export const PUBLIC_DIR = join(WORKING_DIR, "public");

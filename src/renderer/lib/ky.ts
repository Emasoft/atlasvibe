/*
 * Copyright (c) 2024 Emasoft
 *
 * This file is part of AtlasVibe, which is based on Flojoy Studio
 * Original Copyright (c) 2023-2024 Flojoy
 *
 * SPDX-License-Identifier: MIT
 * See the LICENSE file for details.
 */

import { env } from "@/env";
import ky from "ky";

export const captain = ky.create({
  prefixUrl: "http://" + env.VITE_BACKEND_HOST + ":" + env.VITE_BACKEND_PORT,
  credentials: "include",
  timeout: 30000,
});

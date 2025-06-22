/*
 * Copyright (c) 2024 Emasoft
 *
 * This file is part of AtlasVibe, which is based on Flojoy Studio
 * Original Copyright (c) 2023-2024 Flojoy
 *
 * SPDX-License-Identifier: MIT
 * See the LICENSE file for details.
 */

import { BlockData } from "@/renderer/types/block";
import { ReactFlowJsonObject } from "reactflow";
import { defaultApp } from "./apps";

export const NOISY_SINE =
  defaultApp.rfInstance as ReactFlowJsonObject<BlockData>;

export const EMPTY_CANVAS = {
  elements: [],
  position: [0, 0],
  zoom: 0.8,
};

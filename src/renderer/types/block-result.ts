/*
 * Copyright (c) 2024 Emasoft
 *
 * This file is part of AtlasVibe, which is based on Flojoy Studio
 * Original Copyright (c) 2023-2024 Flojoy
 *
 * SPDX-License-Identifier: MIT
 * See the LICENSE file for details.
 */

import { OverridePlotData } from "@/renderer/types/plotly";
import { Layout } from "plotly.js";
import { DataContainer } from "./data-container";

export type BlockResult = {
  plotly_fig?: {
    data: OverridePlotData;
    layout: Partial<Layout> | undefined;
  };
  text_blob?: string;
  data?: DataContainer;
};

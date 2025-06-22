/*
 * Copyright (c) 2024 Emasoft
 *
 * This file is part of AtlasVibe, which is based on Flojoy Studio
 * Original Copyright (c) 2023-2024 Flojoy
 *
 * SPDX-License-Identifier: MIT
 * See the LICENSE file for details.
 */

export const ALL_DC_TYPE = [
  "grayscale",
  "matrix",
  "dataframe",
  "image",
  "ordered_pair",
  "ordered_triple",
  "scalar",
  "plotly",
] as const;

export type DataContainerType = (typeof ALL_DC_TYPE)[number];

export type DataContainer = Scalar;

type Scalar = {
  type: "scalar";
  c: number;
};

// TODO: Add the rest

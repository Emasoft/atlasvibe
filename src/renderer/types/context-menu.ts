/*
 * Copyright (c) 2024 Emasoft
 *
 * This file is part of AtlasVibe, which is based on Flojoy Studio
 * Original Copyright (c) 2023-2024 Flojoy
 *
 * SPDX-License-Identifier: MIT
 * See the LICENSE file for details.
 */

import { Node } from "reactflow";

export type MenuInfo<T> = {
  node: Node<T>;
  top?: number;
  left?: number;
  right?: number;
  bottom?: number;
};

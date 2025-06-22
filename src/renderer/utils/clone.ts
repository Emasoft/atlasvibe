/*
 * Copyright (c) 2024 Emasoft
 *
 * This file is part of AtlasVibe, which is based on Flojoy Studio
 * Original Copyright (c) 2023-2024 Flojoy
 *
 * SPDX-License-Identifier: MIT
 * See the LICENSE file for details.
 */

import { DeepMutable } from "@/renderer/types/util";

export const deepMutableClone = <T>(obj: T): DeepMutable<T> => {
  return JSON.parse(JSON.stringify(obj)) as DeepMutable<T>;
};

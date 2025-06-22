/*
 * Copyright (c) 2024 Emasoft
 *
 * This file is part of AtlasVibe, which is based on Flojoy Studio
 * Original Copyright (c) 2023-2024 Flojoy
 *
 * SPDX-License-Identifier: MIT
 * See the LICENSE file for details.
 */

export function filterMap<T, U>(
  arr: Array<T>,
  mapPred: (x: T) => U | undefined | null,
) {
  return arr.reduce((acc: Array<U>, x: T) => {
    const val = mapPred(x);
    if (val !== undefined && val !== null) {
      acc.push(val);
    }

    return acc;
  }, []);
}

/*
 * Copyright (c) 2024 Emasoft
 *
 * This file is part of AtlasVibe, which is based on Flojoy Studio
 * Original Copyright (c) 2023-2024 Flojoy
 *
 * SPDX-License-Identifier: MIT
 * See the LICENSE file for details.
 */

import { Result, ok, err } from "neverthrow";
import { z } from "zod";

export function tryParse<Z extends z.ZodTypeAny>(
  z: Z,
): (val: unknown) => Result<z.infer<Z>, z.ZodError> {
  return (val: unknown) => {
    const res = z.safeParse(val);
    if (res.success) {
      return ok(res.data as z.infer<Z>);
    }
    return err(res.error);
  };
}

export function pass() {}

/*
 * Copyright (c) 2024 Emasoft
 *
 * This file is part of AtlasVibe, which is based on Flojoy Studio
 * Original Copyright (c) 2023-2024 Flojoy
 *
 * SPDX-License-Identifier: MIT
 * See the LICENSE file for details.
 */

export const matchesQuery = (s: string | undefined, query: string) =>
  Boolean(
    query !== "" &&
      s
        ?.toLocaleLowerCase()
        .split("_")
        .join("")
        .includes(
          query
            .toLocaleLowerCase()
            .split(/[\s_]+/)
            .join(""),
        ),
  );

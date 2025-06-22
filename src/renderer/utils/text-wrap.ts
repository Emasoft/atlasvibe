/*
 * Copyright (c) 2024 Emasoft
 *
 * This file is part of AtlasVibe, which is based on Flojoy Studio
 * Original Copyright (c) 2023-2024 Flojoy
 *
 * SPDX-License-Identifier: MIT
 * See the LICENSE file for details.
 */

export const textWrap = (minWidth: number, fontSize: number, text: string) => {
  const longestWordLength = text
    .split(" ")
    .reduce((acc, cur) => Math.max(acc, cur.length), 0);

  return Math.max(minWidth, longestWordLength * (fontSize - 3));
};

export const getAlphabetAvatar = (username: string) => {
  const splitted = username.split(" ");
  if (splitted.length === 1) {
    return (
      splitted[0].charAt(0).toUpperCase() + splitted[0].charAt(1).toUpperCase()
    );
  }
  return (
    splitted[0].charAt(0).toUpperCase() + splitted[1].charAt(0).toUpperCase()
  );
};

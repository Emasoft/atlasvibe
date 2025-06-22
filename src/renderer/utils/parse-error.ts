/*
 * Copyright (c) 2024 Emasoft
 *
 * This file is part of AtlasVibe, which is based on Flojoy Studio
 * Original Copyright (c) 2023-2024 Flojoy
 *
 * SPDX-License-Identifier: MIT
 * See the LICENSE file for details.
 */

export const parseElectronError = (err: string) => {
  const removeDefaultMsg = err
    .replace(/^(Error:)/, "")
    .replace(/^(Error occurred in handler for)/, "")
    .replace(/^(Error invoking remote method)/, "");
  return removeDefaultMsg.split(":").slice(1).join(":") ?? "";
};

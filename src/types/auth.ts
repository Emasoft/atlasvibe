/*
 * Copyright (c) 2024 Emasoft
 *
 * This file is part of AtlasVibe, which is based on Flojoy Studio
 * Original Copyright (c) 2023-2024 Flojoy
 *
 * SPDX-License-Identifier: MIT
 * See the LICENSE file for details.
 */

export const allRoles = ["Admin", "Operator"] as const;
export type Role = (typeof allRoles)[number];

export type User = {
  name: string;
  role: Role;
  password?: string;
  logged?: boolean;
};

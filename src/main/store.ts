/*
 * Copyright (c) 2024 Emasoft
 *
 * This file is part of AtlasVibe, which is based on Flojoy Studio
 * Original Copyright (c) 2023-2024 Flojoy
 *
 * SPDX-License-Identifier: MIT
 * See the LICENSE file for details.
 */

import Store from "electron-store";
import os from "os";
import { User } from "@/types/auth";

type TypedStore = {
  uvOptionalGroups: string[];
  users: User[];
};

export const store = new Store<TypedStore>({
  defaults: {
    uvOptionalGroups: [],
    users: [
      {
        name: os.userInfo().username,
        role: "Admin",
        logged: true,
      },
    ],
  },
});

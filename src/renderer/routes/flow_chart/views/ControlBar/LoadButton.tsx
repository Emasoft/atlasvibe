/*
 * Copyright (c) 2024 Emasoft
 *
 * This file is part of AtlasVibe, which is based on Flojoy Studio
 * Original Copyright (c) 2023-2024 Flojoy
 *
 * SPDX-License-Identifier: MIT
 * See the LICENSE file for details.
 */

import { MenubarItem, MenubarShortcut } from "@/renderer/components/ui/menubar";
import { useLoadApp } from "@/renderer/hooks/useLoadApp";

export const LoadButton = () => {
  const openFileSelector = useLoadApp();

  return (
    <MenubarItem
      onClick={openFileSelector}
      id="load-app-btn"
      data-testid="load-app-btn"
    >
      {/* TODO: Add logo for windows and linux */}
      Load <MenubarShortcut>⌘O</MenubarShortcut>
    </MenubarItem>
  );
};

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
import { useImportSequences } from "@/renderer/hooks/useTestSequencerProject";

export const ImportSequencesButton = () => {
  const importSequences = useImportSequences();

  return (
    <MenubarItem
      onClick={importSequences}
      id="load-app-btn"
      data-testid="load-app-btn"
    >
      Import sequences<MenubarShortcut>⌘O</MenubarShortcut>
    </MenubarItem>
  );
};

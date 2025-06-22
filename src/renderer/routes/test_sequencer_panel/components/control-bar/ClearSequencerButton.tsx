/*
 * Copyright (c) 2024 Emasoft
 *
 * This file is part of AtlasVibe, which is based on Flojoy Studio
 * Original Copyright (c) 2023-2024 Flojoy
 *
 * SPDX-License-Identifier: MIT
 * See the LICENSE file for details.
 */

import { MenubarItem } from "@/renderer/components/ui/menubar";
import { useSequencerState } from "@/renderer/hooks/useTestSequencerState";

export const ClearSequencerButton = () => {
  const { clearSequencer } = useSequencerState();

  return (
    <MenubarItem
      onClick={clearSequencer}
      id="close-app-btn"
      data-testid="close-app-btn"
    >
      Close sequences
    </MenubarItem>
  );
};

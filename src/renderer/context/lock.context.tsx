/*
 * Copyright (c) 2024 Emasoft
 *
 * This file is part of AtlasVibe, which is based on Flojoy Studio
 * Original Copyright (c) 2023-2024 Flojoy
 *
 * SPDX-License-Identifier: MIT
 * See the LICENSE file for details.
 */

import { createContext, useMemo } from "react";
import { LockedContextType } from "@/renderer/types/test-sequencer";
import { useDisplayedSequenceState } from "@/renderer/hooks/useTestSequencerState";

export const LockedContext = createContext<LockedContextType>(
  {} as LockedContextType,
); // the user can chose to disable certain interactable components

export const LockedContextProvider = ({
  children,
}: {
  children: React.ReactNode;
}) => {
  const { isLocked } = useDisplayedSequenceState();
  const value = useMemo<LockedContextType>(
    () => ({
      isLocked: isLocked,
    }),
    [isLocked],
  );
  return (
    <LockedContext.Provider value={value}>{children}</LockedContext.Provider>
  );
};

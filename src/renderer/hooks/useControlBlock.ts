/*
 * Copyright (c) 2024 Emasoft
 *
 * This file is part of AtlasVibe, which is based on Flojoy Studio
 * Original Copyright (c) 2023-2024 Flojoy
 *
 * SPDX-License-Identifier: MIT
 * See the LICENSE file for details.
 */

import { useProjectStore } from "@/renderer/stores/project";
import { useShallow } from "zustand/react/shallow";

export const useControlBlock = (blockId: string) => {
  const { block, updateBlockParameter } = useProjectStore(
    useShallow((state) => ({
      block: state.nodes.find((node) => node.id === blockId),
      updateBlockParameter: state.updateBlockParameter,
    })),
  );

  return {
    block,
    updateBlockParameter,
  };
};

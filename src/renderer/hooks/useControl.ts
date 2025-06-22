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
import { WidgetData } from "@/renderer/types/control";
import { toast } from "sonner";

export const useControl = (data: WidgetData) => {
  const { block, updateBlockParameter } = useProjectStore(
    useShallow((state) => ({
      block: state.nodes.find((node) => node.id === data.blockId),
      updateBlockParameter: state.updateBlockParameter,
    })),
  );

  if (!block) {
    return undefined;
  }

  const onValueChange = (val: string | number | boolean | null | undefined) => {
    const res = updateBlockParameter(block.id, data.blockParameter, val);
    if (res.isErr()) {
      toast.error("Error updating block parameter", {
        description: res.error.message,
      });
    }
  };

  return {
    block,
    name: block.data.label,
    value: block.data.ctrls[data.blockParameter].value,
    onValueChange,
  };
};

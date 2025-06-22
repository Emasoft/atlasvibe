/*
 * Copyright (c) 2024 Emasoft
 *
 * This file is part of AtlasVibe, which is based on Flojoy Studio
 * Original Copyright (c) 2023-2024 Flojoy
 *
 * SPDX-License-Identifier: MIT
 * See the LICENSE file for details.
 */

import { WidgetProps } from "@/renderer/types/control";
import { NumberInput } from "@/renderer/components/common/NumberInput";
import { WidgetLabel } from "@/renderer/components/common/control-label";
import { useControl } from "@/renderer/hooks/useControl";

export const NumberInputNode = ({ id, data }: WidgetProps) => {
  const control = useControl(data);
  if (!control) {
    return <div className="text-2xl text-red-500">NOT FOUND</div>;
  }
  const { name, value, onValueChange } = control;

  return (
    <div className="flex flex-col items-center gap-2">
      <WidgetLabel
        label={data.label}
        placeholder={`${name} (${data.blockParameter})`}
        id={id}
      />
      <NumberInput
        value={value as number}
        onChange={(val) => onValueChange(val === "" ? undefined : val)}
        className="nodrag text-xl font-bold"
        hideArrows
      />
    </div>
  );
};

/*
 * Copyright (c) 2024 Emasoft
 *
 * This file is part of AtlasVibe, which is based on Flojoy Studio
 * Original Copyright (c) 2023-2024 Flojoy
 *
 * SPDX-License-Identifier: MIT
 * See the LICENSE file for details.
 */

import { memo } from "react";
import { BlockProps } from "@/renderer/types/block";
import DefaultBlock from "./default-block";
import { useBlockIcon } from "@/renderer/hooks/useBlockIcon";

export type AICategory = "AI_ML";

const AIBlock = (props: BlockProps) => {
  const { SvgIcon } = useBlockIcon(
    props.type.toLowerCase().replaceAll("_", "-"),
    props.data.func,
  );

  return (
    <DefaultBlock {...props} variant="accent6">
      {SvgIcon && <SvgIcon />}
    </DefaultBlock>
  );
};

export default memo(AIBlock);

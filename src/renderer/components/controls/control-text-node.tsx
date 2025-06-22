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
import { TextData } from "@/renderer/types/block";
import { NodeProps } from "reactflow";
import TextNode from "@/renderer/components/common/text-node";
import { useShallow } from "zustand/react/shallow";

const ControlTextNode = (props: NodeProps<TextData>) => {
  const { deleteTextNode, updateTextNodeText } = useProjectStore(
    useShallow((state) => ({
      deleteTextNode: state.deleteControlTextNode,
      updateTextNodeText: state.updateControlTextNodeText,
    })),
  );

  return (
    <TextNode
      {...props}
      deleteTextNode={deleteTextNode}
      updateTextNodeText={updateTextNodeText}
    />
  );
};

export default ControlTextNode;

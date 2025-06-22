/*
 * Copyright (c) 2024 Emasoft
 *
 * This file is part of AtlasVibe, which is based on Flojoy Studio
 * Original Copyright (c) 2023-2024 Flojoy
 *
 * SPDX-License-Identifier: MIT
 * See the LICENSE file for details.
 */

import { BlockData } from "@/renderer/types/block";
import { Code, CopyPlus, Info, Pencil, X, Package, FileText } from "lucide-react";
import { useStore, Node } from "reactflow";
import useWithPermission from "@/renderer/hooks/useWithPermission";
import { useFlowchartStore } from "@/renderer/stores/flowchart";
import { useShallow } from "zustand/react/shallow";
import { MenuInfo } from "@/renderer/types/context-menu";
import { ContextMenuAction } from "@/renderer/components/common/context-menu-action";
import { useDeleteBlock } from "@/renderer/stores/project";
import { useState } from "react";
import { SaveBlueprintDialog } from "@/renderer/components/SaveBlueprintDialog";
import { useManifest } from "@/renderer/stores/manifest";
import { VenvStatusDialog } from "@/renderer/components/blocks/VenvStatusDialog";

export type BlockContextMenuInfo = MenuInfo<BlockData> & {
  fullPath: string;
};

type Props = BlockContextMenuInfo & {
  fullPath: string;
  onClick?: () => void;
  duplicateBlock: (node: Node<BlockData>) => void;
  setNodeModalOpen: (open: boolean) => void;
};

export default function BlockContextMenu({
  node,
  top,
  left,
  right,
  bottom,
  fullPath,
  onClick,
  duplicateBlock,
  setNodeModalOpen,
}: Props) {
  const { withPermissionCheck } = useWithPermission();

  const setIsEditMode = useFlowchartStore(
    useShallow((state) => state.setIsEditMode),
  );

  const { addSelectedNodes } = useStore((state) => ({
    resetSelectedElements: state.resetSelectedElements,
    addSelectedNodes: state.addSelectedNodes,
  }));

  const editNode = () => {
    addSelectedNodes([node.id]);
    setIsEditMode(true);
  };

  const openInfo = () => {
    addSelectedNodes([node.id]);
    setIsEditMode(false);
    setNodeModalOpen(true);
  };

  const editPythonCode = async () => {
    await window.api.openEditorWindow(fullPath);
  };

  const duplicate = () => {
    duplicateBlock(node);
  };

  const openInVSC = async () => {
    await window.api.openLink(`vscode://file/${fullPath}`);
  };

  const deleteBlock = useDeleteBlock();

  const [blueprintDialogOpen, setBlueprintDialogOpen] = useState(false);
  const [venvDialogOpen, setVenvDialogOpen] = useState(false);
  const manifest = useManifest();

  // Get existing blueprint names
  const existingBlueprints = manifest
    ? Object.keys(manifest).filter(key => manifest[key].isBlueprint)
    : [];

  const saveAsBlueprint = () => {
    setBlueprintDialogOpen(true);
  };

  const viewEnvironment = () => {
    setVenvDialogOpen(true);
  };

  return (
    <>
    <div
      style={{ top, left, right, bottom }}
      className="absolute z-50 rounded-md border bg-background"
      onClick={onClick}
      data-testid={"block-context-menu"}
    >
      <ContextMenuAction
        testId="context-edit-block"
        onClick={editNode}
        icon={Pencil}
      >
        Edit Block
      </ContextMenuAction>
      <ContextMenuAction
        testId="context-edit-python"
        onClick={withPermissionCheck(editPythonCode)}
        icon={Code}
      >
        Edit Python Code
      </ContextMenuAction>
      <ContextMenuAction
        testId="open-in-vscode"
        onClick={withPermissionCheck(openInVSC)}
        icon={Code}
      >
        Open in VSCode
      </ContextMenuAction>
      <ContextMenuAction
        testId="context-duplicate-block"
        onClick={duplicate}
        icon={CopyPlus}
      >
        Duplicate Block
      </ContextMenuAction>
      {node.data.isCustom && (
        <>
          <ContextMenuAction
            testId="save-as-blueprint-btn"
            onClick={saveAsBlueprint}
            icon={Package}
          >
            Save as Blueprint
          </ContextMenuAction>
          <ContextMenuAction
            testId="view-environment-btn"
            onClick={viewEnvironment}
            icon={FileText}
          >
            View Environment
          </ContextMenuAction>
        </>
      )}
      <hr />
      <ContextMenuAction
        testId="context-block-info"
        onClick={openInfo}
        icon={Info}
      >
        Block Info
      </ContextMenuAction>
      <hr />
      <ContextMenuAction
        testId="context-delete-block"
        onClick={() => deleteBlock(node.id)}
        icon={X}
      >
        Delete Block
      </ContextMenuAction>
    </div>
    <SaveBlueprintDialog
      open={blueprintDialogOpen}
      onOpenChange={setBlueprintDialogOpen}
      blockId={node.id}
      blockPath={node.data.path}
      defaultName={node.data.label}
      existingBlueprints={existingBlueprints}
    />
    {node.data.isCustom && node.data.path && (
      <VenvStatusDialog
        open={venvDialogOpen}
        onOpenChange={setVenvDialogOpen}
        blockPath={node.data.path}
        blockName={node.data.label}
      />
    )}
    </>
  );
}

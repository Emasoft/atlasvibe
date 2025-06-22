/*
 * Copyright (c) 2024 Emasoft
 *
 * This file is part of AtlasVibe, which is based on Flojoy Studio
 * Original Copyright (c) 2023-2024 Flojoy
 *
 * SPDX-License-Identifier: MIT
 * See the LICENSE file for details.
 */

import React, { CSSProperties, memo, useState, useMemo } from "react";
import clsx from "clsx";
import { BlockProps } from "@/renderer/types/block";
import NodeWrapper from "@/renderer/components/common/NodeWrapper";
import HandleComponent from "@/renderer/components/common/HandleComponent";
import NodeInput from "@/renderer/components/common/NodeInput";
import { useBlockStatus } from "@/renderer/hooks/useBlockStatus";
import { BlockLabel } from "@/renderer/components/common/block-label";
import { TVariant } from "@/renderer/types/tailwind";
import { variantClassMap } from "@/renderer/lib/utils";
import { useProjectStore } from "@/renderer/stores/project";
import { useShallow } from "zustand/react/shallow";
import { RegeneratingIndicator } from "@/renderer/components/common/RegeneratingIndicator";
import { useManifestStore } from "@/renderer/stores/manifest";
import "../BlockRegenerationStyles.css";

type DefaultBlockProps = BlockProps & {
  width?: CSSProperties["width"];
  height?: number;
  children?: React.ReactNode;
  variant?: TVariant;
  showLabel?: boolean;
  className?: string;
  labelPosition?: "left" | "right" | "center";
  wrapperStyle?: CSSProperties;
};

const DefaultBlock = ({
  selected,
  data,
  width,
  height,
  children,
  variant = "accent1",
  showLabel = true,
  className,
  labelPosition,
  wrapperStyle,
}: DefaultBlockProps) => {
  const [isRenamingTitle, setIsRenamingTitle] = useState(false);
  const { blockRunning, blockError } = useBlockStatus(data.id);
  const { updateBlockLabel, blocksWithPendingChanges } = useProjectStore(
    useShallow((state) => ({
      updateBlockLabel: state.updateBlockLabel,
      blocksWithPendingChanges: state.blocksWithPendingChanges,
    })),
  );
  const regeneratingBlocks = useManifestStore((state) => state.regeneratingBlocks);

  // Check if this block is regenerating based on its path
  const isRegenerating = useMemo(() => {
    if (!data.path) return false;
    return regeneratingBlocks.has(data.path);
  }, [data.path, regeneratingBlocks]);

  // Check if this block has pending changes
  const hasPendingChanges = useMemo(() => {
    return blocksWithPendingChanges.has(data.id);
  }, [data.id, blocksWithPendingChanges]);

  const maxInputOutput = useMemo(
    () => Math.max(data.inputs?.length ?? 0, data.outputs?.length ?? 0),
    [data.inputs?.length, data.outputs?.length],
  );

  return (
    <NodeWrapper
      nodeError={blockError}
      data={data}
      selected={selected}
      style={wrapperStyle}
    >
      <RegeneratingIndicator visible={isRegenerating} />
      {hasPendingChanges && !isRegenerating && (
        <div className="absolute -top-6 left-1/2 -translate-x-1/2 rounded-full bg-blue-500 px-2 py-0.5 text-xs font-semibold text-white animate-pulse">
          Pending Changes
        </div>
      )}
      <div
        className={clsx(
          `${isRegenerating ? 'block-regenerating' : hasPendingChanges ? 'border-blue-500' : variantClassMap[variant].border} relative flex min-h-[96px] items-center justify-center rounded-lg border-2 border-solid p-2 transition-all duration-300`,
          {
            [`shadow-around ${isRegenerating ? 'shadow-yellow-500' : hasPendingChanges ? 'shadow-blue-500' : variantClassMap[variant].shadow}`]:
              blockRunning || selected || isRegenerating || hasPendingChanges,
          },
          { "shadow-around shadow-red-700": blockError },
          className,
        )}
        style={{
          width: width,
          minHeight: height || maxInputOutput * 58 + 38,
        }}
        onDoubleClick={() => setIsRenamingTitle(true)}
      >
        {isRenamingTitle ? (
          <NodeInput
            title={data.label}
            id={data.id}
            setIsRenamingTitle={setIsRenamingTitle}
            updateLabel={updateBlockLabel}
            className="w-full px-2 font-sans text-2xl font-extrabold tracking-wider"
          />
        ) : (
          children ?? <BlockLabel label={data.label} variant={variant} />
        )}
        <HandleComponent data={data} variant={variant} />
      </div>
      {showLabel && children && (
        <BlockLabel
          label={data.label}
          variant={variant}
          labelPosition={labelPosition}
        />
      )}
    </NodeWrapper>
  );
};

export default memo(DefaultBlock);

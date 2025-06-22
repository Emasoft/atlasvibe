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
import { useBlockResults } from "@/renderer/hooks/useBlockResults";
import saveAs from "file-saver";

export const ExportResultButton = () => {
  const blockResults = useBlockResults();

  const exportResultDisabled = Object.keys(blockResults).length == 0;

  const downloadResult = async () => {
    if (!blockResults.length) return;
    const json = JSON.stringify(blockResults, null, 2);
    const blob = new Blob([json], { type: "text/plain;charset=utf-8" });

    saveAs(blob, "output.json");
  };

  return (
    <MenubarItem
      onClick={downloadResult}
      className={exportResultDisabled ? "disabled" : ""}
      disabled={exportResultDisabled}
    >
      Export Result
    </MenubarItem>
  );
};

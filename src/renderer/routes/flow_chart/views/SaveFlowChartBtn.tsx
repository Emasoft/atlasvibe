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
import saveAs from "file-saver";
import * as htmlToImage from "html-to-image";

const SaveFlowChartBtn = () => {
  const downloadResult = async () => {
    const flowChartDiv = document.getElementById("flow-chart");
    if (!flowChartDiv) {
      alert("No flow chart found on current page!");
      return;
    }
    const dataUrl = await htmlToImage.toJpeg(flowChartDiv);
    const res = await fetch(dataUrl);
    const blob = await res.blob();

    saveAs(blob, "output.jpeg");
  };

  return (
    <MenubarItem onClick={downloadResult}>Save Flowchart as JPEG</MenubarItem>
  );
};

export default SaveFlowChartBtn;

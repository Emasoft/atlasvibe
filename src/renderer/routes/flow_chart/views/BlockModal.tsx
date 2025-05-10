// Copyright (c) 2024 Emasoft (for atlasvibe modifications and derivative work)
// Copyright (c) 2024 Flojoy (for the original "Flojoy Studio" software)
//
// This software is licensed under the MIT License.
// Refer to the LICENSE file for more details.

import { Light as SyntaxHighlighter } from "react-syntax-highlighter";
import python from "react-syntax-highlighter/dist/cjs/languages/hljs/python";
import json from "react-syntax-highlighter/dist/cjs/languages/hljs/json";
import { JSONTree } from "react-json-tree";
import { Node } from "reactflow";
import { atlasvibeSyntaxTheme } from "@/renderer/assets/AtlasVibeTheme";
import PlotlyComponent from "@/renderer/components/plotly/PlotlyComponent";
import { makePlotlyData } from "@/renderer/components/plotly/formatPlotlyData";
import MarkDownText from "@/renderer/components/common/MarkDownText";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/renderer/components/ui/dialog";
import { BlockResult } from "@/renderer/types/block-result";
import { BlockData } from "@/renderer/stores/project"; 
import { ScrollArea, ScrollBar } from "@/renderer/components/ui/scroll-area";
import { useTheme } from "@/renderer/providers/theme-provider";
import { Button } from "@/renderer/components/ui/button";
import useWithPermission from "@/renderer/hooks/useWithPermission";
// import { env } from "@/env"; // Vite handles env vars via import.meta.env
import { useBlockStatus } from "@/renderer/hooks/useBlockStatus";
import { toast } from "sonner";

const jsonTheme = {
  scheme: "atlasvibe",
  author: "Jack",
  base00: "rgb(var(--color-modal))",
  base01: "rgb(var(--color-accent3))",
  base02: "rgb(var(--color-accent3))",
  base03: "rgb(var(--color-accent2))",
  base04: "rgb(var(--color-accent1))",
  base05: "rgb(var(--color-accent3))",
  base06: "rgb(var(--color-accent2))",
  base07: "rgb(var(--color-accent2))",
  base08: "rgb(var(--color-accent3))",
  base09: "rgb(var(--color-accent1))",
  base0A: "rgb(var(--color-accent1))",
  base0B: "rgb(var(--color-accent3))",
  base0C: "rgb(var(--foreground))",
  base0D: "rgb(var(--foreground))",
  base0E: "rgb(var(--color-accent1))",
  base0F: "rgb(var(--color-accent1))",
};

// Import only the languages needed to reduce bundle size
SyntaxHighlighter.registerLanguage("python", python);
SyntaxHighlighter.registerLanguage("json", json);

export type BlockModalProps = {
  modalIsOpen: boolean;
  setModalOpen: (open: boolean) => void;
  pythonString: string;
  blockFilePath: string;
  blockFullPath: string;
  selectedNode: Node<BlockData>; 
};

const BlockModal = ({
  modalIsOpen,
  setModalOpen,
  blockFilePath,
  blockFullPath,
  pythonString,
  selectedNode,
}: BlockModalProps) => {
  const { resolvedTheme } = useTheme();
  const { withPermissionCheck } = useWithPermission();
  const { blockResult } = useBlockStatus(selectedNode.id);

  const path = blockFilePath.replace(/"\\"/g, "/");

  const link =
    path.startsWith("/") || path.includes(":")
      ? null
      : `${import.meta.env.VITE_ATLASVIBE_REPO}/blocks/${path}`; 

  const docsLink = `${import.meta.env.VITE_ATLASVIBE_DOCS_LINK}/blocks/${path 
    .split("/")
    .slice(0, -1)
    .join("/")}`.toLowerCase();

  const handleEditCode = async () => {
    await window.api.openEditorWindow(blockFullPath);
    toast.info(
      "If you edit and save the block code, you may need to manually trigger a manifest refresh or restart the application for changes to fully reflect, depending on current backend capabilities.",
    );
  };

  const isDevMode = import.meta.env.DEV; 
  const isCustomBlock = !!selectedNode.data.isCustom;


  return (
    <Dialog open={modalIsOpen} onOpenChange={setModalOpen}>
      <DialogContent className="my-12 max-h-screen overflow-y-scroll border-muted bg-background p-12 sm:max-w-2xl md:max-w-4xl">
        <DialogHeader>
          <DialogTitle className="text-3xl">
            {selectedNode?.data.func}
          </DialogTitle>
        </DialogHeader>
        {link && (
          <div className="flex gap-x-4">
            <a
              className="rounded-full border border-accent1 px-6 py-2 text-sm font-semibold uppercase text-accent1 duration-200 hover:bg-accent1/10"
              href={link}
              target="_blank"
            >
              View on GitHub
            </a>
            <a
              className="rounded-full border border-accent1 px-6 py-2 text-sm font-semibold uppercase text-accent1 duration-200 hover:bg-accent1/10"
              href={docsLink}
              target="_blank"
            >
              View Examples
            </a>
          </div>
        )}
        <div className="py-1" />
        <h3 className="text-gray-800 dark:text-gray-200">
          Function Type:{" "}
          <code className="text-accent1">{selectedNode.data.type}</code>
        </h3>
        {blockResult && (
          <NodeModalDataViz
            result={blockResult}
            theme={resolvedTheme}
            selectedNode={selectedNode}
          />
        )}
        <div className="py-0.5" />
        <h2 className="text-lg font-semibold text-muted-foreground">
          Python code
        </h2>

        <div className="flex gap-2">
          <Button
            onClick={withPermissionCheck(handleEditCode)}
            data-testid="btn-edit-python"
            variant="secondary"
            disabled={!isCustomBlock && !isDevMode} 
          >
            Edit Python Code
            {isCustomBlock || isDevMode ? "" : " (Read-only)"}
          </Button>
          <Button
            onClick={withPermissionCheck(
              async () =>
                await window.api.openLink(`vscode://file/${blockFullPath}`),
            )}
            data-testid="btn-open-vscode"
            variant="secondary"
          >
            Open in VSCode
          </Button>
        </div>

        <ScrollArea className="h-full w-full rounded-lg">
          <ScrollBar orientation="vertical" />
          <ScrollBar orientation="horizontal" />
          <SyntaxHighlighter language="python" style={atlasvibeSyntaxTheme}>
            {pythonString}
          </SyntaxHighlighter>
        </ScrollArea>
        <div className="py-2" />
        <h2 className="text-lg font-semibold text-muted-foreground">
          Block data
        </h2>
        <div
          className="rounded-md bg-modal px-4"
          data-testid="block-info-json"
          data-blockjson={JSON.stringify(selectedNode)}
        >
          <JSONTree
            data={selectedNode}
            theme={{
              extend: jsonTheme,
            }}
            labelRenderer={([key]) => (
              <span style={{ paddingLeft: 8 }}>{key}</span>
            )}
          />
        </div>
        <div className="py-2" />
      </DialogContent>
    </Dialog>
  );
};

type NodeModalDataVizProps = {
  result: BlockResult;
  selectedNode: Node<BlockData>; 
  theme: "light" | "dark";
};

const NodeModalDataViz = ({
  result,
  selectedNode,
  theme,
}: NodeModalDataVizProps) => {
  return (
    <div>
      {result.text_blob && (
        <div className="h-[600px] overflow-auto rounded-md bg-modal sm:max-w-xl md:max-w-4xl">
          <MarkDownText text={result.text_blob} />
        </div>
      )}
      {result.plotly_fig && (
        <div className="flex justify-center">
          <PlotlyComponent
            data={makePlotlyData(result.plotly_fig.data, theme)}
            layout={{
              ...result.plotly_fig.layout,
              title: result.plotly_fig.layout?.title ?? selectedNode.data.func,
            }}
            useResizeHandler
            theme={theme}
          />
        </div>
      )}
    </div>
  );
};

export default BlockModal;

import CodeMirror from "@uiw/react-codemirror";
import { python } from "@codemirror/lang-python";
import { vscodeDark } from "@uiw/codemirror-theme-vscode";
import { useParams } from "react-router-dom";
import { useEffect, useState } from "react";
import { Button } from "@/renderer/components/ui/button";
import useKeyboardShortcut from "@/renderer/hooks/useKeyboardShortcut";
import invariant from "tiny-invariant";
import { toast } from "sonner";
import { updateBlockCode } from "@/renderer/lib/api";
import { useProjectStore } from "@/renderer/stores/project";
import { useManifestStore } from "@/renderer/stores/manifest";

const EditorView = () => {
  const { id } = useParams<{ id: string }>();

  // Joey: https://github.com/remix-run/react-router/issues/8498
  invariant(id, "Error: ID isn't set for the editor view route!");

  const fullPath = atob(id);

  const [value, setValue] = useState("");
  const [hasChanged, setHasChanged] = useState<boolean>(false);
  const [isCustomBlock, setIsCustomBlock] = useState<boolean>(false);

  const loadFile = async () => {
    const res = await window.api.loadFileFromFullPath(fullPath);
    setValue(res);
    
    // Check if this is a custom block
    setIsCustomBlock(fullPath.includes("atlasvibe_blocks") && fullPath.endsWith(".py"));
  };

  const saveFile = async () => {
    const res = await window.api.saveFileToFullPath(fullPath, value);
    if (res.isOk()) {
      setHasChanged(false);
      
      // Check if this is a custom block file (contains "atlasvibe_blocks" in path)
      if (fullPath.includes("atlasvibe_blocks") && fullPath.endsWith(".py")) {
        // Get the current project path
        const projectPath = useProjectStore.getState().path;
        
        if (projectPath) {
          // Update block code on backend to regenerate metadata
          const updateRes = await updateBlockCode(fullPath, value, projectPath);
          
          if (updateRes.isOk()) {
            toast.success("Block updated successfully", {
              description: "Metadata has been regenerated"
            });
            
            // Refresh manifests to reflect the changes
            const { fetchManifest } = useManifestStore.getState();
            await fetchManifest();
          } else {
            toast.error("Failed to update block metadata", {
              description: updateRes.error.message
            });
          }
        }
      }
    } else {
      toast.error("Error when trying to save file", {
        description: res.error?.message || "Unknown error",
      });
    }
  };

  const handleChange = (value: string) => {
    setValue(value);
    setHasChanged(true);
  };

  useEffect(() => {
    loadFile();
  }, []);

  useKeyboardShortcut("ctrl", "s", () => saveFile());
  useKeyboardShortcut("meta", "s", () => saveFile());

  return (
    <div>
      <div className="absolute right-5 z-50 flex items-center gap-2 p-4">
        {isCustomBlock && (
          <div className="text-sm text-muted-foreground">Custom Block</div>
        )}
        {hasChanged && <div className="">Changed</div>}
        <Button onClick={saveFile}>Save</Button>
        <Button asChild>
          <a href={`vscode://file/${fullPath}`}>Open in VSCode</a>
        </Button>
      </div>
      <CodeMirror
        value={value}
        style={{
          height: `calc(100vh - 48px)`,
        }}
        height="100%"
        className=""
        extensions={[python()]}
        theme={vscodeDark}
        onChange={handleChange}
      />
    </div>
  );
};

export default EditorView;

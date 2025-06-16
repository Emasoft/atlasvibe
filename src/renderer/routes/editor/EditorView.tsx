import CodeMirror from "@uiw/react-codemirror";
import { python } from "@codemirror/lang-python";
import { vscodeDark } from "@uiw/codemirror-theme-vscode";
import { linter, lintGutter } from "@codemirror/lint";
import { autocompletion, completionKeymap } from "@codemirror/autocomplete";
import { defaultKeymap } from "@codemirror/commands";
import { keymap } from "@codemirror/view";
import { useParams } from "react-router-dom";
import { useEffect, useState } from "react";
import { Button } from "@/renderer/components/ui/button";
import { Badge } from "@/renderer/components/ui/badge";
import { AlertCircle, CheckCircle2, Info } from "lucide-react";
import useKeyboardShortcut from "@/renderer/hooks/useKeyboardShortcut";
import invariant from "tiny-invariant";
import { toast } from "sonner";
import { updateBlockCode } from "@/renderer/lib/api";
import { useProjectStore } from "@/renderer/stores/project";
import { useManifestStore } from "@/renderer/stores/manifest";
import { pythonLinter } from "@/renderer/lib/editor/python-linting";
import { pythonCompletions } from "@/renderer/lib/editor/python-completions";
import { Alert, AlertDescription, AlertTitle } from "@/renderer/components/ui/alert";

const EditorView = () => {
  const { id } = useParams<{ id: string }>();

  // Joey: https://github.com/remix-run/react-router/issues/8498
  invariant(id, "Error: ID isn't set for the editor view route!");

  const fullPath = atob(id);

  const [value, setValue] = useState("");
  const [hasChanged, setHasChanged] = useState<boolean>(false);
  const [isCustomBlock, setIsCustomBlock] = useState<boolean>(false);
  const [docstringValid, setDocstringValid] = useState<boolean>(true);
  const [syntaxErrors] = useState<number>(0);

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
    
    // Check docstring validity for AtlasVibe blocks
    if (isCustomBlock && value.includes("@atlasvibe")) {
      const hasValidDocstring = checkDocstringFormat(value);
      setDocstringValid(hasValidDocstring);
    }
  };

  const checkDocstringFormat = (code: string): boolean => {
    const functionMatch = code.match(/@atlasvibe[\s\S]*?def\s+\w+\([^)]*\)[\s\S]*?"""([\s\S]*?)"""/);
    if (!functionMatch) return false;
    
    const docstring = functionMatch[1];
    const hasParameters = /Parameters\s*\n\s*-+/.test(docstring);
    const hasReturns = /Returns\s*\n\s*-+/.test(docstring);
    
    return hasParameters && hasReturns;
  };

  useEffect(() => {
    loadFile();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useKeyboardShortcut("ctrl", "s", () => saveFile());
  useKeyboardShortcut("meta", "s", () => saveFile());

  // Configure extensions
  const extensions = [
    python(),
    lintGutter(),
    linter(pythonLinter),
    autocompletion({
      override: [pythonCompletions],
      defaultKeymap: true,
    }),
    keymap.of([
      ...defaultKeymap,
      ...completionKeymap,
    ]),
  ];

  return (
    <div className="flex flex-col h-screen">
      <div className="flex items-center justify-between p-4 border-b">
        <div className="flex items-center gap-4">
          <h2 className="text-lg font-semibold">
            {fullPath.split('/').pop()}
          </h2>
          {isCustomBlock && (
            <Badge variant="secondary">Custom Block</Badge>
          )}
          {hasChanged && (
            <Badge variant="outline">Modified</Badge>
          )}
        </div>
        
        <div className="flex items-center gap-4">
          {isCustomBlock && (
            <div className="flex items-center gap-2">
              {docstringValid ? (
                <Badge variant="outline" className="gap-1">
                  <CheckCircle2 className="w-3 h-3" />
                  Docstring OK
                </Badge>
              ) : (
                <Badge variant="destructive" className="gap-1">
                  <AlertCircle className="w-3 h-3" />
                  Invalid Docstring
                </Badge>
              )}
            </div>
          )}
          
          <Button onClick={saveFile} disabled={!hasChanged}>
            Save
          </Button>
          <Button variant="outline" asChild>
            <a href={`vscode://file/${fullPath}`}>Open in VSCode</a>
          </Button>
        </div>
      </div>

      {isCustomBlock && !docstringValid && (
        <Alert className="m-4">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Invalid Docstring Format</AlertTitle>
          <AlertDescription>
            AtlasVibe blocks require NumPy-style docstrings with <code>Parameters</code> and <code>Returns</code> sections.
            The backend uses these docstrings to generate block metadata.
          </AlertDescription>
        </Alert>
      )}

      <div className="flex-1 overflow-hidden">
        <CodeMirror
          value={value}
          height="100%"
          extensions={extensions}
          theme={vscodeDark}
          onChange={handleChange}
          basicSetup={{
            lineNumbers: true,
            foldGutter: true,
            dropCursor: true,
            allowMultipleSelections: true,
            indentOnInput: true,
            bracketMatching: true,
            closeBrackets: true,
            autocompletion: true,
            rectangularSelection: true,
            highlightSelectionMatches: true,
            searchKeymap: true,
          }}
        />
      </div>

      <div className="flex items-center justify-between px-4 py-2 border-t text-sm text-muted-foreground">
        <div className="flex items-center gap-4">
          <span>Python</span>
          {syntaxErrors > 0 && (
            <span className="text-destructive">
              {syntaxErrors} error{syntaxErrors > 1 ? 's' : ''}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Info className="w-3 h-3" />
          <span>Ctrl+Space for suggestions • Ctrl+S to save</span>
        </div>
      </div>
    </div>
  );
};

export default EditorView;

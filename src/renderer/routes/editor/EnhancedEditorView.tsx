/*
 * Copyright (c) 2024 Emasoft
 *
 * This file is part of AtlasVibe, which is based on Flojoy Studio
 * Original Copyright (c) 2023-2024 Flojoy
 *
 * SPDX-License-Identifier: MIT
 * See the LICENSE file for details.
 */

import CodeMirror from "@uiw/react-codemirror";
import { python } from "@codemirror/lang-python";
import { vscodeDark } from "@uiw/codemirror-theme-vscode";
import { linter, lintGutter, Diagnostic } from "@codemirror/lint";
import {
  autocompletion,
  completionKeymap,
  CompletionContext,
} from "@codemirror/autocomplete";
import { defaultKeymap } from "@codemirror/commands";
import {
  keymap,
  ViewUpdate,
  EditorView as CMEditorView,
} from "@codemirror/view";
import { useParams } from "react-router-dom";
import { useEffect, useState, useMemo, useRef, useCallback } from "react";
import { Button } from "@/renderer/components/ui/button";
import { Badge } from "@/renderer/components/ui/badge";
import {
  AlertCircle,
  CheckCircle2,
  Info,
  ChevronUp,
  ChevronDown,
  Loader2,
  FileCode,
  Bug,
  Lightbulb,
  Terminal,
  Package,
} from "lucide-react";
import useKeyboardShortcut from "@/renderer/hooks/useKeyboardShortcut";
import invariant from "tiny-invariant";
import { toast } from "sonner";
import {
  updateBlockCode,
  validateCode,
  getCompletions,
  formatCode,
  getVenvStatus,
} from "@/renderer/lib/api";
import { useProjectStore } from "@/renderer/stores/project";
import { useManifestStore } from "@/renderer/stores/manifest";
import {
  Alert,
  AlertDescription,
  AlertTitle,
} from "@/renderer/components/ui/alert";
import { ScrollArea } from "@/renderer/components/ui/scroll-area";
import { cn } from "@/renderer/lib/utils";
import { debounce } from "lodash";

interface ValidationError {
  line: number;
  column: number;
  message: string;
  severity: "error" | "warning" | "info";
  category: string;
  suggestion?: string;
}

interface VenvStatus {
  exists: boolean;
  valid: boolean;
  python_version?: string;
  last_regenerated?: string;
  health_checks?: Array<{
    name: string;
    status: string;
    message: string;
  }>;
}

const EnhancedEditorView = () => {
  const { id } = useParams<{ id: string }>();
  invariant(id, "Error: ID isn't set for the editor view route!");

  const fullPath = atob(id);
  const editorRef = useRef<CMEditorView | null>(null);

  const [value, setValue] = useState("");
  const [hasChanged, setHasChanged] = useState<boolean>(false);
  const [isCustomBlock, setIsCustomBlock] = useState<boolean>(false);
  const [errors, setErrors] = useState<ValidationError[]>([]);
  const [isValidating, setIsValidating] = useState<boolean>(false);
  const [errorPanelOpen, setErrorPanelOpen] = useState<boolean>(true);
  const [selectedError, setSelectedError] = useState<ValidationError | null>(
    null,
  );
  const [venvStatus, setVenvStatus] = useState<VenvStatus | null>(null);
  const [isFormattingCode, setIsFormattingCode] = useState<boolean>(false);

  const loadFile = async () => {
    const res = await window.api.loadFileFromFullPath(fullPath);
    setValue(res);

    // Check if this is a custom block
    const isCustom =
      fullPath.includes("atlasvibe_blocks") && fullPath.endsWith(".py");
    setIsCustomBlock(isCustom);

    // Validate initial content
    if (isCustom) {
      await validateCurrentCode(res);
      await loadVenvStatus();
    }
  };

  const saveFile = async () => {
    const res = await window.api.saveFileToFullPath(fullPath, value);
    if (res.isOk()) {
      setHasChanged(false);

      if (isCustomBlock) {
        const projectPath = useProjectStore.getState().path;

        if (projectPath) {
          const updateRes = await updateBlockCode(fullPath, value, projectPath);

          if (updateRes.isOk()) {
            const response = updateRes.value;

            if (response.status === "queued") {
              toast.info("Block update queued", {
                description: `Block is currently executing. Changes will be applied when it finishes.`,
              });
            } else {
              toast.success("Block updated successfully", {
                description: `Version ${response.version + 1}`,
              });
            }

            // Always refresh manifest to get latest state
            const { fetchManifest } = useManifestStore.getState();
            await fetchManifest();
          } else {
            toast.error("Failed to update block", {
              description: updateRes.error.message,
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

  const validateCurrentCode = async (code: string) => {
    if (!isCustomBlock) return;

    setIsValidating(true);
    try {
      const projectPath = useProjectStore.getState().path;
      const result = await validateCode(
        code,
        fullPath.split("/").pop() || "unknown.py",
        projectPath,
      );

      if (result.isOk()) {
        const validationResult = result.value as { errors: any[] };
        const validationErrors = validationResult.errors.map((err: any) => ({
          ...err,
          severity: err.severity as "error" | "warning" | "info",
        }));
        setErrors(validationErrors);
      }
    } catch (error) {
      console.error("Validation error:", error);
    } finally {
      setIsValidating(false);
    }
  };

  const loadVenvStatus = async () => {
    if (!isCustomBlock) return;

    try {
      const blockPath = fullPath.substring(0, fullPath.lastIndexOf("/"));
      const response = await getVenvStatus(blockPath);
      if (response.isOk()) {
        setVenvStatus(response.value);
      }
    } catch (error) {
      console.error("Failed to load venv status:", error);
    }
  };

  const formatCurrentCode = async () => {
    setIsFormattingCode(true);
    try {
      const result = await formatCode(value);
      if (result.isOk()) {
        const formatResult = result.value as {
          changed: boolean;
          formatted: string;
          error?: string;
        };
        if (formatResult.changed) {
          setValue(formatResult.formatted);
          setHasChanged(true);
          toast.success("Code formatted successfully");
        } else {
          toast.info("Code is already formatted");
        }
      } else {
        toast.error("Failed to format code", {
          description: result.isErr() ? result.error.message : "Unknown error",
        });
      }
    } catch (error) {
      toast.error("Failed to format code");
    } finally {
      setIsFormattingCode(false);
    }
  };

  // Debounced validation
  const debouncedValidate = useMemo(
    () => debounce((code: string) => validateCurrentCode(code), 500),
    [isCustomBlock],
  );

  const handleChange = (value: string, viewUpdate: ViewUpdate) => {
    setValue(value);
    setHasChanged(true);

    // Trigger validation
    if (isCustomBlock) {
      debouncedValidate(value);
    }
  };

  const navigateToError = (error: ValidationError) => {
    if (editorRef.current) {
      const doc = editorRef.current.state.doc;
      const line = doc.line(error.line);
      const pos = line.from + error.column;

      editorRef.current.dispatch({
        selection: { anchor: pos, head: pos },
        scrollIntoView: true,
      });

      editorRef.current.focus();
    }
    setSelectedError(error);
  };

  // Custom linter that uses our validation errors
  const enhancedPythonLinter = useCallback(() => {
    return (view: CMEditorView): Diagnostic[] => {
      return errors.map((error) => ({
        from: view.state.doc.line(error.line).from + error.column,
        to: view.state.doc.line(error.line).from + error.column + 1,
        severity: error.severity,
        message: error.message,
        source: error.category,
      }));
    };
  }, [errors]);

  // Enhanced autocomplete with backend integration
  const enhancedCompletions = async (context: CompletionContext) => {
    const projectPath = useProjectStore.getState().path;
    const line = context.state.doc.lineAt(context.pos).number;
    const column = context.pos - context.state.doc.line(line).from;

    try {
      const result = await getCompletions(
        context.state.doc.toString(),
        line,
        column,
        context.matchBefore(/\w*/)?.text,
        projectPath,
      );

      if (result.isOk()) {
        return {
          from: context.pos - (context.matchBefore(/\w*/)?.text.length || 0),
          options: (result.value as { completions: any[] }).completions.map(
            (comp: any) => ({
              label: comp.label,
              type: comp.kind,
              detail: comp.detail,
              info: comp.documentation,
              apply: comp.insertText,
            }),
          ),
        };
      }
    } catch (error) {
      console.error("Failed to get completions:", error);
    }

    return null;
  };

  useEffect(() => {
    loadFile();
  }, []);

  useKeyboardShortcut("ctrl", "s", () => saveFile());
  useKeyboardShortcut("meta", "s", () => saveFile());
  // TODO: Add support for multiple modifiers in useKeyboardShortcut hook

  // Configure extensions
  const extensions = useMemo(
    () => [
      python(),
      lintGutter(),
      linter(enhancedPythonLinter()),
      autocompletion({
        override: [enhancedCompletions],
        defaultKeymap: true,
      }),
      keymap.of([...defaultKeymap, ...completionKeymap]),
      CMEditorView.updateListener.of((update: ViewUpdate) => {
        if (update.docChanged) {
          handleChange(update.state.doc.toString(), update);
        }
      }),
    ],
    [enhancedPythonLinter],
  );

  const errorCount = errors.filter((e) => e.severity === "error").length;
  const warningCount = errors.filter((e) => e.severity === "warning").length;

  return (
    <div className="flex h-screen flex-col">
      {/* Header */}
      <div className="flex items-center justify-between border-b p-4">
        <div className="flex items-center gap-4">
          <FileCode className="h-5 w-5" />
          <h2 className="text-lg font-semibold">{fullPath.split("/").pop()}</h2>
          {isCustomBlock && <Badge variant="secondary">Custom Block</Badge>}
          {hasChanged && <Badge variant="outline">Modified</Badge>}
          {isValidating && (
            <Badge variant="outline" className="gap-1">
              <Loader2 className="h-3 w-3 animate-spin" />
              Validating...
            </Badge>
          )}
        </div>

        <div className="flex items-center gap-4">
          {/* Error/Warning Summary */}
          {isCustomBlock && (
            <div className="flex items-center gap-2">
              {errorCount > 0 && (
                <Badge variant="destructive" className="gap-1">
                  <Bug className="h-3 w-3" />
                  {errorCount} error{errorCount !== 1 ? "s" : ""}
                </Badge>
              )}
              {warningCount > 0 && (
                <Badge variant="outline" className="gap-1 text-yellow-600">
                  <AlertCircle className="h-3 w-3" />
                  {warningCount} warning{warningCount !== 1 ? "s" : ""}
                </Badge>
              )}
              {errorCount === 0 && warningCount === 0 && !isValidating && (
                <Badge variant="outline" className="gap-1 text-green-600">
                  <CheckCircle2 className="h-3 w-3" />
                  No issues
                </Badge>
              )}
            </div>
          )}

          {/* Action Buttons */}
          <Button
            variant="outline"
            size="sm"
            onClick={formatCurrentCode}
            disabled={isFormattingCode}
          >
            {isFormattingCode ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              "Format"
            )}
          </Button>

          <Button onClick={saveFile} disabled={!hasChanged}>
            Save
          </Button>

          <Button variant="outline" asChild>
            <a href={`vscode://file/${fullPath}`}>Open in VSCode</a>
          </Button>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Code Editor */}
        <div
          className={cn(
            "flex-1 overflow-hidden",
            errorPanelOpen && errors.length > 0 ? "flex-1" : "flex-1",
          )}
        >
          <CodeMirror
            value={value}
            height="100%"
            extensions={extensions}
            theme={vscodeDark}
            onCreateEditor={(view) => {
              editorRef.current = view;
            }}
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

        {/* Error Panel */}
        {isCustomBlock && errors.length > 0 && (
          <div
            className={cn(
              "border-t transition-all duration-300",
              errorPanelOpen ? "h-64" : "h-10",
            )}
          >
            {/* Error Panel Header */}
            <div
              className="flex cursor-pointer items-center justify-between bg-muted/50 px-4 py-2"
              onClick={() => setErrorPanelOpen(!errorPanelOpen)}
            >
              <div className="flex items-center gap-2">
                <Terminal className="h-4 w-4" />
                <span className="font-medium">Problems</span>
                <Badge variant="outline" className="ml-2">
                  {errors.length}
                </Badge>
              </div>
              <Button variant="ghost" size="sm">
                {errorPanelOpen ? (
                  <ChevronDown className="h-4 w-4" />
                ) : (
                  <ChevronUp className="h-4 w-4" />
                )}
              </Button>
            </div>

            {/* Error List */}
            {errorPanelOpen && (
              <ScrollArea className="h-[calc(100%-2.5rem)] flex-1">
                <div className="p-2">
                  {errors.map((error, index) => (
                    <div
                      key={index}
                      className={cn(
                        "mb-2 cursor-pointer rounded-md p-3 transition-colors",
                        "hover:bg-muted/50",
                        selectedError === error && "bg-muted",
                        error.severity === "error" &&
                          "border-l-4 border-destructive",
                        error.severity === "warning" &&
                          "border-l-4 border-yellow-500",
                        error.severity === "info" &&
                          "border-l-4 border-blue-500",
                      )}
                      onClick={() => navigateToError(error)}
                    >
                      <div className="flex items-start gap-2">
                        {error.severity === "error" && (
                          <Bug className="mt-0.5 h-4 w-4 text-destructive" />
                        )}
                        {error.severity === "warning" && (
                          <AlertCircle className="mt-0.5 h-4 w-4 text-yellow-500" />
                        )}
                        {error.severity === "info" && (
                          <Info className="mt-0.5 h-4 w-4 text-blue-500" />
                        )}

                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <span className="font-medium">{error.message}</span>
                            <span className="text-sm text-muted-foreground">
                              Line {error.line}, Column {error.column}
                            </span>
                          </div>

                          {error.suggestion && (
                            <div className="mt-1 flex items-start gap-1">
                              <Lightbulb className="mt-0.5 h-3 w-3 text-yellow-500" />
                              <span className="text-sm text-muted-foreground">
                                {error.suggestion}
                              </span>
                            </div>
                          )}

                          <span className="text-xs text-muted-foreground">
                            [{error.category}]
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            )}
          </div>
        )}
      </div>

      {/* Status Bar */}
      <div className="flex items-center justify-between border-t px-4 py-2 text-sm text-muted-foreground">
        <div className="flex items-center gap-4">
          <span>Python</span>
          {venvStatus && (
            <div className="flex items-center gap-2">
              <Package className="h-3 w-3" />
              <span>
                {venvStatus.valid
                  ? `Python ${venvStatus.python_version || "Unknown"}`
                  : "No venv"}
              </span>
            </div>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Info className="h-3 w-3" />
          <span>
            Ctrl+Space for suggestions • Ctrl+S to save • Ctrl+Shift+F to format
          </span>
        </div>
      </div>
    </div>
  );
};

export default EnhancedEditorView;

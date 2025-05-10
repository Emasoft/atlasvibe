import { contextBridge, ipcRenderer } from "electron"; 
// import api from "../api/index"; // Base api object, if it exists and has pre-defined non-IPC functions
import { InterpretersList } from "src/main/python/interpreter"; 
import { BlockDefinition } from "@/renderer/types/manifest"; 

// Define a type for the extended API
// This should match the handlers you set up in your main process
export interface ExtendedWindowApi {
  // Functions from original api (if any, otherwise remove this spread)
  // This assumes `api` from `../api/index` has its own type that Window["api"] would match
  // For a cleaner approach, explicitly list all expected functions.
  // [key: string]: any; // Fallback for existing api properties not explicitly typed here

  restartAtlasVibe: () => void;
  createCustomBlockFromBlueprint: (
    blueprintKey: string,
    newCustomBlockName: string,
    projectPath: string,
  ) => Promise<BlockDefinition | undefined>; 
  
  checkPythonInstallation: (force?: boolean) => Promise<InterpretersList>;
  setPythonInterpreter: (path: string) => Promise<void>;
  installPipx: () => Promise<void>;
  pipxEnsurepath: () => Promise<void>;
  installPoetry: () => Promise<void>;
  installDependencies: () => Promise<void>; 
  spawnCaptain: () => Promise<void>; // Should be spawnAtlasVibeEngine
  browsePyInterpreter: () => Promise<string | undefined>;
  openLogFolder: () => void; // Changed to void to match ipcRenderer.send
  isPackaged: () => boolean;
  openEditorWindow: (filePath: string) => void; // Changed to void
  openLink: (url: string) => void;
  getFileContent: (filePath: string) => Promise<string>;
  saveFile: (filePath: string, content: string) => Promise<void>;
  saveFileAs: (defaultFilename: string, content: string, allowedExtensions?: string[]) => Promise<{ filePath?: string; canceled: boolean }>;
  setUnsavedChanges: (hasChanges: boolean) => void;
}

const extendedApi: ExtendedWindowApi = {
  // ...(api as any), // If you have a base api object, spread it here. Otherwise, remove.
  
  checkPythonInstallation: (force?: boolean) => ipcRenderer.invoke("check-python-installation", force),
  setPythonInterpreter: (path: string) => ipcRenderer.invoke("set-python-interpreter", path),
  installPipx: () => ipcRenderer.invoke("install-pipx"),
  pipxEnsurepath: () => ipcRenderer.invoke("pipx-ensurepath"),
  installPoetry: () => ipcRenderer.invoke("install-poetry"),
  installDependencies: () => ipcRenderer.invoke("install-dependencies"),
  spawnCaptain: () => ipcRenderer.invoke("spawn-atlasvibe-engine"), 
  browsePyInterpreter: () => ipcRenderer.invoke("browse-py-interpreter"),
  openLogFolder: () => ipcRenderer.send("open-log-folder"), 
  isPackaged: () => ipcRenderer.sendSync("is-packaged"), 
  openEditorWindow: (filePath: string) => ipcRenderer.send("open-editor-window", filePath), 
  openLink: (url: string) => ipcRenderer.send("open-link", url),
  getFileContent: (filePath: string) => ipcRenderer.invoke("get-file-content", filePath),
  saveFile: (filePath: string, content: string) => ipcRenderer.invoke("save-file", filePath, content),
  saveFileAs: (defaultFilename: string, content: string, allowedExtensions?: string[]) => ipcRenderer.invoke("save-file-as", defaultFilename, content, allowedExtensions),
  setUnsavedChanges: (hasChanges: boolean) => ipcRenderer.send("set-unsaved-changes", hasChanges),

  restartAtlasVibe: () => ipcRenderer.send("restart-app"), 
  createCustomBlockFromBlueprint: (blueprintKey, newCustomBlockName, projectPath) =>
    ipcRenderer.invoke("create-custom-block", blueprintKey, newCustomBlockName, projectPath),
};

if (process.contextIsolated) {
  try {
    contextBridge.exposeInMainWorld("api", extendedApi);
  } catch (error) {
    console.error('Failed to expose "api" to main world:', error);
  }
} else {
  // @ts-expect-error (define global api)
  window.api = extendedApi;
}

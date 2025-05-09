import { contextBridge, ipcRenderer } from "electron"; 
import api from "../api/index";
import { InterpretersList } from "src/main/python/interpreter"; // Ensure this path is correct
import { BlockDefinition } from "@/renderer/types/manifest"; // Assuming BlockDefinition is the return type

// Define a type for the extended API
// This should match the handlers you set up in your main process
export interface ExtendedWindowApi extends Window["api"] {
  restartAtlasVibe: () => void;
  createCustomBlockFromBlueprint: (
    blueprintKey: string,
    newCustomBlockName: string,
    projectPath: string,
  ) => Promise<BlockDefinition | undefined>; // Updated return type
  // Add other new IPC functions here as they are implemented in main
  checkPythonInstallation: (force?: boolean) => Promise<InterpretersList>;
  setPythonInterpreter: (path: string) => Promise<void>;
  installPipx: () => Promise<void>;
  pipxEnsurepath: () => Promise<void>;
  installPoetry: () => Promise<void>;
  installDependencies: () => Promise<void>; 
  spawnCaptain: () => Promise<void>; // Should be spawnAtlasVibeEngine or similar
  browsePyInterpreter: () => Promise<string | undefined>;
  openLogFolder: () => Promise<void>;
  isPackaged: () => boolean;
  openEditorWindow: (filePath: string) => Promise<void>;
  // Potentially more functions based on your API needs
}

const extendedApi: ExtendedWindowApi = {
  ...api,
  // Ensure all functions used in renderer are defined here and map to IPC calls
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
  openLink: (url: string) => ipcRenderer.send("open-link", url), // Added missing openLink
  getFileContent: (filePath: string) => ipcRenderer.invoke("get-file-content", filePath), // Added missing getFileContent
  saveFile: (filePath: string, content: string) => ipcRenderer.invoke("save-file", filePath, content), // Added missing saveFile
  saveFileAs: (defaultFilename: string, content: string, allowedExtensions?: string[]) => ipcRenderer.invoke("save-file-as", defaultFilename, content, allowedExtensions), // Added missing saveFileAs
  setUnsavedChanges: (hasChanges: boolean) => ipcRenderer.send("set-unsaved-changes", hasChanges), // Added missing setUnsavedChanges


  restartAtlasVibe: () => ipcRenderer.send("restart-app"), 
  createCustomBlockFromBlueprint: (blueprintKey, newCustomBlockName, projectPath) =>
    ipcRenderer.invoke("create-custom-block", blueprintKey, newCustomBlockName, projectPath),
};


// Use `contextBridge` APIs to expose Electron APIs to
// renderer only if context isolation is enabled, otherwise
// just add to the DOM global.
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

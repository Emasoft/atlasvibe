import { contextBridge, ipcRenderer } from "electron"; 
import api from "../api/index";
import { InterpretersList } from "src/main/python/interpreter"; // Ensure this path is correct

// Define a type for the extended API
// This should match the handlers you set up in your main process
export interface ExtendedWindowApi extends Window["api"] {
  restartAtlasVibe: () => void;
  createCustomBlockFromBlueprint: (
    blueprintKey: string,
    newCustomBlockName: string,
    projectPath: string,
  ) => Promise<any>; // Adjust 'any' to the actual return type (e.g., BlockDefinition from your types)
  // Add other new IPC functions here as they are implemented in main
  checkPythonInstallation: (force?: boolean) => Promise<InterpretersList>;
  setPythonInterpreter: (path: string) => Promise<void>;
  installPipx: () => Promise<void>;
  pipxEnsurepath: () => Promise<void>;
  installPoetry: () => Promise<void>;
  installDependencies: () => Promise<void>; // Assuming this is for Python deps via Poetry
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
  // For example, if `api.checkPythonInstallation` was part of the original `api` from `../api/index`
  // and it's already an IPC call, it might not need re-definition here unless its signature changed.
  // The TS errors suggest some of these might be missing or their signatures are incompatible.

  // Placeholder implementations for functions that were causing TS errors,
  // assuming they will be implemented via IPC.
  // You need to ensure these have corresponding handlers in your Electron main process.
  checkPythonInstallation: (force?: boolean) => ipcRenderer.invoke("check-python-installation", force),
  setPythonInterpreter: (path: string) => ipcRenderer.invoke("set-python-interpreter", path),
  installPipx: () => ipcRenderer.invoke("install-pipx"),
  pipxEnsurepath: () => ipcRenderer.invoke("pipx-ensurepath"),
  installPoetry: () => ipcRenderer.invoke("install-poetry"),
  installDependencies: () => ipcRenderer.invoke("install-dependencies"),
  spawnCaptain: () => ipcRenderer.invoke("spawn-atlasvibe-engine"), // Renamed to reflect new backend
  browsePyInterpreter: () => ipcRenderer.invoke("browse-py-interpreter"),
  openLogFolder: () => ipcRenderer.send("open-log-folder"),
  isPackaged: () => ipcRenderer.sendSync("is-packaged"), // Example of sync call if needed
  openEditorWindow: (filePath: string) => ipcRenderer.send("open-editor-window", filePath),


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

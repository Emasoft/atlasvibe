import { contextBridge, ipcRenderer } from "electron"; // Added ipcRenderer
import api from "../api/index";

// Define a type for the extended API
// This should match the handlers you set up in your main process
export interface ExtendedWindowApi extends Window["api"] {
  restartAtlasVibe: () => void;
  createCustomBlockFromBlueprint: (
    blueprintKey: string,
    newCustomBlockName: string,
    projectPath: string,
  ) => Promise<any>; // Adjust 'any' to the actual return type (BlockDefinition)
  // Add other new IPC functions here
}

const extendedApi: ExtendedWindowApi = {
  ...api,
  restartAtlasVibe: () => ipcRenderer.send("restart-app"), // Example channel name
  createCustomBlockFromBlueprint: (blueprintKey, newCustomBlockName, projectPath) =>
    ipcRenderer.invoke("create-custom-block", blueprintKey, newCustomBlockName, projectPath), // Example channel name
  // Define other new functions
};


// Use `contextBridge` APIs to expose Electron APIs to
// renderer only if context isolation is enabled, otherwise
// just add to the DOM global.
if (process.contextIsolated) {
  contextBridge.exposeInMainWorld("api", extendedApi);
} else {
  window.api = extendedApi;
}

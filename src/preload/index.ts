import { contextBridge, ipcRenderer } from "electron"; 
// import api from "../api/index"; // Base api object, if it exists and has pre-defined non-IPC functions
import { InterpretersList } from "src/main/python/interpreter"; 
import { BlockDefinition } from "@/renderer/types/manifest"; 

// Define a type for the extended API
// This should match the handlers you set up in your main process
export interface ExtendedWindowApi {
  // File operations
  loadFileFromFullPath: (filepath: string) => Promise<string>;
  saveFileToFullPath: (filepath: string, content: string) => Promise<{ isOk: () => boolean; error?: { message: string } }>;
  saveFileToDisk: (filepath: string, content: string) => Promise<boolean>;
  getFileContent: (filePath: string) => Promise<string>;
  saveFile: (filePath: string, content: string) => Promise<void>;
  saveFileAs: (defaultFilename: string, content: string, allowedExtensions?: string[]) => Promise<{ filePath?: string; canceled: boolean }>;
  openFilePicker: (allowedExtensions?: string[]) => Promise<{ filePath: string; fileContent: string } | undefined>;
  openFilesPicker: (allowedExtensions?: string[], title?: string) => Promise<{ filePath: string; fileContent: string }[] | undefined>;
  openAllFilesInFolder: (folderPath: string, allowedExtensions?: string[], relativeToResources?: boolean) => Promise<{ filePath: string; fileContent: string }[] | undefined>;
  openTestPicker: () => Promise<{ filePath: string; fileContent: string }>;
  isFileOnDisk: (filepath: string) => Promise<boolean>;
  pickDirectory: (allowDirectoryCreation: boolean) => Promise<string>;
  getCustomBlocksDir: () => Promise<string | undefined>;
  cacheCustomBlocksDir: (dirPath: string) => void;
  
  // Python/Poetry operations
  checkPythonInstallation: (force?: boolean) => Promise<InterpretersList>;
  setPythonInterpreter: (path: string) => Promise<void>;
  browsePyInterpreter: () => Promise<string | undefined>;
  installPipx: () => Promise<void>;
  pipxEnsurepath: () => Promise<void>;
  installPoetry: () => Promise<void>;
  installDependencies: () => Promise<void>;
  poetryShowTopLevel: () => Promise<any[]>;
  poetryShowUserGroup: () => Promise<any[]>;
  poetryGetGroupInfo: () => Promise<any[]>;
  poetryInstallDepGroup: (group: string) => Promise<boolean>;
  poetryUninstallDepGroup: (group: string) => Promise<boolean>;
  poetryInstallDepUserGroup: (dep: string) => Promise<boolean>;
  poetryUninstallDepUserGroup: (dep: string) => Promise<boolean>;
  poetryInstallRequirementsUserGroup: (filePath: string) => Promise<boolean>;
  
  // System operations
  spawnCaptain: () => Promise<void>;
  restartCaptain: () => Promise<void>;
  restartAtlasVibe: () => void;
  openLogFolder: () => void;
  downloadLogs: () => void;
  isPackaged: () => boolean;
  openEditorWindow: (filePath: string) => void;
  openLink: (url: string) => void;
  setUnsavedChanges: (hasChanges: boolean) => void;
  subscribeToElectronLogs: (func: (arg: string) => void) => void;
  checkForUpdates: () => void;
  
  // Network/Debug operations
  ping: (addr: string) => Promise<string>;
  netstat: () => Promise<string>;
  ifconfig: () => Promise<string>;
  listPythonPackages: () => Promise<string>;
  pyvisaInfo: () => Promise<string>;
  
  // Auth operations
  getUserProfiles: () => Promise<any[]>;
  setUserProfile: (username: string) => void;
  setUserProfilePassword: (username: string, password: string) => Promise<void>;
  validatePassword: (username: string, password: string) => Promise<boolean>;
  createUserProfile: (user: any) => Promise<void>;
  deleteUserProfile: (username: string, currentUser: any) => Promise<void>;
  
  // Block operations
  createCustomBlockFromBlueprint: (
    blueprintKey: string,
    newCustomBlockName: string,
    projectPath: string,
  ) => Promise<BlockDefinition | undefined>;
}

const extendedApi: ExtendedWindowApi = {
  // File operations
  loadFileFromFullPath: (filepath: string) => ipcRenderer.invoke("load-file-from-full-path", filepath),
  saveFileToFullPath: (filepath: string, content: string) => ipcRenderer.invoke("save-file-to-full-path", filepath, content),
  saveFileToDisk: (filepath: string, content: string) => ipcRenderer.invoke("write-file-sync", filepath, content),
  getFileContent: (filePath: string) => ipcRenderer.invoke("get-file-content", filePath),
  saveFile: (filePath: string, content: string) => ipcRenderer.invoke("save-file", filePath, content),
  saveFileAs: (defaultFilename: string, content: string, allowedExtensions?: string[]) => ipcRenderer.invoke("save-file-as", defaultFilename, content, allowedExtensions),
  openFilePicker: (allowedExtensions?: string[]) => ipcRenderer.invoke("open-file-picker", allowedExtensions),
  openFilesPicker: (allowedExtensions?: string[], title?: string) => ipcRenderer.invoke("open-files-picker", allowedExtensions, title),
  openAllFilesInFolder: (folderPath: string, allowedExtensions?: string[], relativeToResources?: boolean) => ipcRenderer.invoke("open-all-files-in-folder-picker", folderPath, allowedExtensions, relativeToResources),
  openTestPicker: () => ipcRenderer.invoke("open-test-picker"),
  isFileOnDisk: (filepath: string) => ipcRenderer.invoke("is-file-on-disk", filepath),
  pickDirectory: (allowDirectoryCreation: boolean) => ipcRenderer.invoke("pick-directory", allowDirectoryCreation),
  getCustomBlocksDir: () => ipcRenderer.invoke("get-custom-blocks-dir"),
  cacheCustomBlocksDir: (dirPath: string) => ipcRenderer.send("cache-custom-blocks-dir", dirPath),
  
  // Python/Poetry operations
  checkPythonInstallation: (force?: boolean) => ipcRenderer.invoke("check-python-installation", force),
  setPythonInterpreter: (path: string) => ipcRenderer.invoke("set-python-interpreter", path),
  browsePyInterpreter: () => ipcRenderer.invoke("browse-py-interpreter"),
  installPipx: () => ipcRenderer.invoke("install-pipx"),
  pipxEnsurepath: () => ipcRenderer.invoke("pipx-ensurepath"),
  installPoetry: () => ipcRenderer.invoke("install-poetry"),
  installDependencies: () => ipcRenderer.invoke("install-dependencies"),
  poetryShowTopLevel: () => ipcRenderer.invoke("poetry-show-top-level"),
  poetryShowUserGroup: () => ipcRenderer.invoke("poetry-show-user-group"),
  poetryGetGroupInfo: () => ipcRenderer.invoke("poetry-get-group-info"),
  poetryInstallDepGroup: (group: string) => ipcRenderer.invoke("poetry-install-dep-group", group),
  poetryUninstallDepGroup: (group: string) => ipcRenderer.invoke("poetry-uninstall-dep-group", group),
  poetryInstallDepUserGroup: (dep: string) => ipcRenderer.invoke("poetry-install-dep-user-group", dep),
  poetryUninstallDepUserGroup: (dep: string) => ipcRenderer.invoke("poetry-uninstall-dep-user-group", dep),
  poetryInstallRequirementsUserGroup: (filePath: string) => ipcRenderer.invoke("poetry-install-requirements-user-group", filePath),
  
  // System operations
  spawnCaptain: () => ipcRenderer.invoke("spawn-atlasvibe-engine"),
  restartCaptain: () => ipcRenderer.invoke("restart-captain"),
  restartAtlasVibe: () => ipcRenderer.send("restart-app"),
  openLogFolder: () => ipcRenderer.send("open-log-folder"),
  downloadLogs: () => ipcRenderer.send("download-logs"),
  isPackaged: () => ipcRenderer.sendSync("is-packaged"),
  openEditorWindow: (filePath: string) => ipcRenderer.send("open-editor-window", filePath),
  openLink: (url: string) => ipcRenderer.send("open-link", url),
  setUnsavedChanges: (hasChanges: boolean) => ipcRenderer.send("set-unsaved-changes", hasChanges),
  subscribeToElectronLogs: (func: (arg: string) => void) => {
    ipcRenderer.on("statusbar-logging", (event, data: string) => func(data));
  },
  checkForUpdates: () => ipcRenderer.send("check-for-updates"),
  
  // Network/Debug operations
  ping: (addr: string) => ipcRenderer.invoke("ping", addr),
  netstat: () => ipcRenderer.invoke("netstat"),
  ifconfig: () => ipcRenderer.invoke("ifconfig"),
  listPythonPackages: () => ipcRenderer.invoke("list-python-packages"),
  pyvisaInfo: () => ipcRenderer.invoke("pyvisa-info"),
  
  // Auth operations
  getUserProfiles: () => ipcRenderer.invoke("get-user-profiles"),
  setUserProfile: (username: string) => ipcRenderer.send("set-user-profile", username),
  setUserProfilePassword: (username: string, password: string) => ipcRenderer.invoke("set-user-profile-password", username, password),
  validatePassword: (username: string, password: string) => ipcRenderer.invoke("validate-password", username, password),
  createUserProfile: (user: any) => ipcRenderer.invoke("create-user-profile", user),
  deleteUserProfile: (username: string, currentUser: any) => ipcRenderer.invoke("delete-user-profile", username, currentUser),
  
  // Block operations
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
  // @ts-ignore (define global api)
  window.api = extendedApi;
}

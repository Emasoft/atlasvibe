import { contextBridge, ipcRenderer } from "electron"; 
import { API } from "../api/index";
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
  selectFolder: () => Promise<{ filePaths: string[]; canceled: boolean }>;
  pathExists: (path: string) => Promise<boolean>;
  createDirectory: (path: string) => Promise<void>;
  showConfirmDialog: (options: {
    title: string;
    message: string;
    buttons: string[];
    defaultId?: number;
    cancelId?: number;
  }) => Promise<{ response: number }>;
  logTransaction: (transaction: string) => void;
  
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
  isPackaged: () => Promise<boolean>;
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
  loadFileFromFullPath: (filepath: string) => ipcRenderer.invoke(API.loadFileFromFullPath, filepath),
  saveFileToFullPath: (filepath: string, content: string) => ipcRenderer.invoke(API.saveFileToFullPath, filepath, content),
  saveFileToDisk: (filepath: string, content: string) => ipcRenderer.invoke(API.writeFileSync, filepath, content),
  getFileContent: (filePath: string) => ipcRenderer.invoke(API.getFileContent, filePath),
  saveFile: (filePath: string, content: string) => ipcRenderer.send(API.writeFileSync, filePath, content),
  saveFileAs: async (defaultFilename: string, content: string, allowedExtensions?: string[]) => {
    const result = await ipcRenderer.invoke(API.showSaveDialog, defaultFilename, allowedExtensions);
    if (result.filePath) {
      ipcRenderer.send(API.writeFileSync, result.filePath, content);
    }
    return result;
  },
  openFilePicker: (allowedExtensions?: string[]) => ipcRenderer.invoke(API.openFilePicker, allowedExtensions),
  openFilesPicker: (allowedExtensions?: string[], title?: string) => ipcRenderer.invoke(API.openFilesPicker, allowedExtensions, title),
  openAllFilesInFolder: (folderPath: string, allowedExtensions?: string[], relativeToResources?: boolean) => ipcRenderer.invoke(API.openAllFilesInFolderPicker, folderPath, allowedExtensions, relativeToResources),
  openTestPicker: () => ipcRenderer.invoke(API.openTestPicker),
  isFileOnDisk: (filepath: string) => ipcRenderer.invoke(API.isFileOnDisk, filepath),
  pickDirectory: (allowDirectoryCreation: boolean) => ipcRenderer.invoke(API.pickDirectory, allowDirectoryCreation),
  getCustomBlocksDir: () => ipcRenderer.invoke(API.getCustomBlocksDir),
  cacheCustomBlocksDir: (dirPath: string) => ipcRenderer.send(API.cacheCustomBlocksDir, dirPath),
  selectFolder: () => ipcRenderer.invoke(API.selectFolder),
  pathExists: (path: string) => ipcRenderer.invoke(API.pathExists, path),
  createDirectory: (path: string) => ipcRenderer.invoke(API.createDirectory, path),
  showConfirmDialog: (options) => ipcRenderer.invoke(API.showConfirmDialog, options),
  logTransaction: (transaction: string) => ipcRenderer.send(API.logTransaction, transaction),
  
  // Python/Poetry operations
  checkPythonInstallation: (force?: boolean) => ipcRenderer.invoke(API.checkPythonInstallation, force),
  setPythonInterpreter: (path: string) => ipcRenderer.invoke(API.setPythonInterpreter, path),
  browsePyInterpreter: () => ipcRenderer.invoke(API.browsePythonInterpreter),
  installPipx: () => ipcRenderer.invoke(API.installPipx),
  pipxEnsurepath: () => ipcRenderer.invoke(API.pipxEnsurepath),
  installPoetry: () => ipcRenderer.invoke(API.installPoetry),
  installDependencies: () => ipcRenderer.invoke(API.installDependencies),
  poetryShowTopLevel: () => ipcRenderer.invoke(API.poetryShowTopLevel),
  poetryShowUserGroup: () => ipcRenderer.invoke(API.poetryShowUserGroup),
  poetryGetGroupInfo: () => ipcRenderer.invoke(API.poetryGetGroupInfo),
  poetryInstallDepGroup: (group: string) => ipcRenderer.invoke(API.poetryInstallDepGroup, group),
  poetryUninstallDepGroup: (group: string) => ipcRenderer.invoke(API.poetryUninstallDepGroup, group),
  poetryInstallDepUserGroup: (dep: string) => ipcRenderer.invoke(API.poetryInstallDepUserGroup, dep),
  poetryUninstallDepUserGroup: (dep: string) => ipcRenderer.invoke(API.poetryUninstallDepUserGroup, dep),
  poetryInstallRequirementsUserGroup: (filePath: string) => ipcRenderer.invoke(API.poetryInstallRequirementsUserGroup, filePath),
  
  // System operations
  spawnCaptain: () => ipcRenderer.invoke(API.spawnCaptain),
  restartCaptain: () => ipcRenderer.invoke(API.restartCaptain),
  restartAtlasVibe: () => ipcRenderer.send(API.restartAtlasvibeStudio),
  openLogFolder: () => ipcRenderer.invoke(API.openLogFolder),
  downloadLogs: () => ipcRenderer.send(API.downloadLogs),
  isPackaged: () => ipcRenderer.invoke(API.isPackaged),
  openEditorWindow: (filePath: string) => ipcRenderer.invoke(API.openEditorWindow, filePath),
  openLink: (url: string) => ipcRenderer.invoke(API.openLink, url),
  setUnsavedChanges: (hasChanges: boolean) => ipcRenderer.send(API.setUnsavedChanges, hasChanges),
  subscribeToElectronLogs: (func: (arg: string) => void) => {
    ipcRenderer.on(API.statusBarLogging, (event, data: string) => func(data));
  },
  checkForUpdates: () => ipcRenderer.send(API.checkForUpdates),
  
  // Network/Debug operations
  ping: (addr: string) => ipcRenderer.invoke(API.ping, addr),
  netstat: () => ipcRenderer.invoke(API.netstat),
  ifconfig: () => ipcRenderer.invoke(API.ifconfig),
  listPythonPackages: () => ipcRenderer.invoke(API.listPythonPackages),
  pyvisaInfo: () => ipcRenderer.invoke(API.pyvisaInfo),
  
  // Auth operations
  getUserProfiles: () => ipcRenderer.invoke(API.getUserProfiles),
  setUserProfile: (username: string) => ipcRenderer.send(API.setUserProfile, username),
  setUserProfilePassword: (username: string, password: string) => ipcRenderer.invoke(API.setUserProfilePassword, username, password),
  validatePassword: (username: string, password: string) => ipcRenderer.invoke(API.validatePassword, username, password),
  createUserProfile: (user: any) => ipcRenderer.invoke(API.createUserProfile, user),
  deleteUserProfile: (username: string, currentUser: any) => ipcRenderer.invoke(API.deleteUserProfile, username, currentUser),
  
  // Block operations
  createCustomBlockFromBlueprint: (blueprintKey, newCustomBlockName, projectPath) =>
    ipcRenderer.invoke(API.createCustomBlock, blueprintKey, newCustomBlockName, projectPath),
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

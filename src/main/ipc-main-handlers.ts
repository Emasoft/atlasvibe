import { API } from "@/api";
import {
  cacheCustomBlocksDir,
  getCustomBlocksDir,
  ifconfig,
  loadFileFromFullPath,
  netstat,
  openFilePicker,
  pickDirectory,
  ping,
  readFileSync,
  saveFileToFullPath,
  writeFileSync,
  isFileOnDisk,
  openFilesPicker,
  openAllFilesInFolderPicker,
} from "./utils";
import {
  getAllLogs,
  handleDownloadLogs,
  logListener,
  openLogFolder,
  sendToStatusBar,
} from "./logging";
import { app, dialog, ipcMain, shell } from "electron";
import { checkForUpdates } from "./update";
import {
  checkPythonInstallation,
  installDependencies,
  installUv,
  ensureUvEnvironment,
  killCaptain,
  listPythonPackages,
  uvEnsurepath,
  pyvisaInfo,
  restartCaptain,
  spawnCaptain,
} from "./python";
import {
  browsePythonInterpreter,
  handlePythonInterpreter,
} from "./python/interpreter";
import {
  uvGetGroupInfo,
  uvInstallDepGroup,
  uvInstallDepUserGroup,
  uvInstallRequirementsUserGroup,
  uvShowTopLevel,
  uvShowUserGroup,
  uvUninstallDepGroup,
  uvUninstallDepUserGroup,
} from "./python/uv";
import { createEditorWindow } from "./window";
import {
  createUserProfile,
  deleteUserProfile,
  getUsers,
  setUserProfile,
  setUserProfilePassword,
  validatePassword,
} from "@/api/services/auth-service";

const handleSetUnsavedChanges = (_, value: boolean) => {
  global.hasUnsavedChanges = value;
};

const handleShowSaveAsDialog = async (
  _,
  defaultFilename: string,
  allowedExtensions: string[] = ["json"],
) => {
  return await dialog.showSaveDialog({
    defaultPath: defaultFilename,
    filters: [
      {
        name: "allowed extensions",
        extensions: allowedExtensions,
      },
    ],
  });
};
/**
 * @access: Only can be called from index.ts file
 */
export const registerIpcMainHandlers = () => {
  ipcMain.on(API.setUnsavedChanges, handleSetUnsavedChanges);
  ipcMain.on(API.writeFileSync, writeFileSync);
  ipcMain.on(API.statusBarLogging, logListener);
  ipcMain.on(API.sendLogToStatusbar, (_, ...logs) =>
    sendToStatusBar(logs.join(" ")),
  );
  ipcMain.on(API.downloadLogs, handleDownloadLogs);
  ipcMain.on(API.checkForUpdates, checkForUpdates);
  ipcMain.on(API.cacheCustomBlocksDir, cacheCustomBlocksDir);
  ipcMain.handle(API.setupExecutionTime, async () => {
    const end = performance.now();
    const executionTimeInSeconds = (end - global.setupStarted) / 1000;
    return await Promise.resolve(executionTimeInSeconds);
  });
  ipcMain.handle(API.isCI, () => {
    return Promise.resolve(process.env.CI === "true");
  });
  ipcMain.handle(API.isDev, () => {
    return Promise.resolve(!app.isPackaged);
  });
  ipcMain.handle(API.getAllLogs, getAllLogs);
  ipcMain.handle(API.writeFile, writeFileSync);
  ipcMain.handle(API.getCustomBlocksDir, getCustomBlocksDir);
  ipcMain.handle(API.restartCaptain, restartCaptain);
  ipcMain.handle(API.setPythonInterpreter, handlePythonInterpreter);
  ipcMain.handle(API.showSaveDialog, handleShowSaveAsDialog);
  ipcMain.handle(API.checkPythonInstallation, checkPythonInstallation);
  ipcMain.handle(API.installPipx, installUv); // Keep API name for compatibility
  ipcMain.handle(API.pipxEnsurepath, uvEnsurepath); // Keep API name for compatibility
  ipcMain.handle(API.installPoetry, ensureUvEnvironment); // Keep API name for compatibility
  ipcMain.handle(API.installDependencies, installDependencies);
  ipcMain.handle(API.writeFileSync, writeFileSync);
  ipcMain.handle(API.spawnCaptain, spawnCaptain);
  ipcMain.handle(API.killCaptain, killCaptain);
  ipcMain.handle(API.openLogFolder, openLogFolder);
  ipcMain.handle(API.pickDirectory, pickDirectory);
  ipcMain.handle(API.browsePythonInterpreter, browsePythonInterpreter);
  ipcMain.handle(API.listPythonPackages, listPythonPackages);
  ipcMain.handle(API.pyvisaInfo, pyvisaInfo);
  ipcMain.handle(API.ping, (_, addr) => ping(addr));
  ipcMain.handle(API.netstat, netstat);
  ipcMain.handle(API.ifconfig, ifconfig);
  ipcMain.handle(API.restartAtlasvibeStudio, () => {
    app.relaunch();
    app.exit();
  });

  // Keep Poetry API names for compatibility but use uv functions
  ipcMain.handle(API.poetryShowTopLevel, uvShowTopLevel);
  ipcMain.handle(API.poetryShowUserGroup, uvShowUserGroup);
  ipcMain.handle(API.poetryGetGroupInfo, uvGetGroupInfo);
  ipcMain.handle(API.poetryInstallDepGroup, (_, group) => {
    return uvInstallDepGroup(group);
  });
  ipcMain.handle(API.poetryUninstallDepGroup, (_, group) => {
    return uvUninstallDepGroup(group);
  });
  ipcMain.handle(API.poetryUninstallDepUserGroup, (_, dep) => {
    return uvUninstallDepUserGroup(dep);
  });
  ipcMain.handle(API.poetryInstallDepUserGroup, (_, dep) => {
    return uvInstallDepUserGroup(dep);
  });
  ipcMain.handle(API.poetryInstallRequirementsUserGroup, (_, filePath) => {
    return uvInstallRequirementsUserGroup(filePath);
  });
  ipcMain.handle(API.openFilePicker, openFilePicker);
  ipcMain.handle(API.openFilesPicker, openFilesPicker);
  ipcMain.handle(API.openAllFilesInFolderPicker, openAllFilesInFolderPicker);

  ipcMain.handle(
    API.openTestPicker,
    async (e) => await openFilePicker(e, "Test", ["json", "py", "robot"]),
  );
  ipcMain.handle(API.openEditorWindow, (_, filepath) => {
    createEditorWindow(filepath);
  });

  ipcMain.handle(API.loadFileFromFullPath, (_, filepath) => {
    return loadFileFromFullPath(filepath);
  });

  ipcMain.handle(API.saveFileToFullPath, (_, filepath, fileContent) => {
    return saveFileToFullPath(filepath, fileContent);
  });
  ipcMain.handle(API.openLink, (_, url) => {
    shell.openExternal(url);
  });
  // Authentication
  ipcMain.handle(API.getUserProfiles, async () => {
    return Promise.resolve(getUsers());
  });
  ipcMain.on(API.setUserProfile, setUserProfile);
  ipcMain.handle(API.setUserProfilePassword, setUserProfilePassword);
  ipcMain.handle(API.validatePassword, validatePassword);
  ipcMain.handle(API.createUserProfile, createUserProfile);
  ipcMain.handle(API.deleteUserProfile, deleteUserProfile);
  ipcMain.handle(API.getFileContent, readFileSync);
  ipcMain.handle(API.isFileOnDisk, isFileOnDisk);
  
  // Custom block creation handler
  ipcMain.handle("create-custom-block", async (_, blueprintKey: string, newCustomBlockName: string, projectPath: string) => {
    try {
      // Get the backend URL from environment or default
      const backendUrl = process.env.BACKEND_URL || "http://localhost:5392";
      
      // Call the backend API to create the custom block
      const response = await fetch(`${backendUrl}/blocks/create-custom/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          blueprint_key: blueprintKey,
          new_block_name: newCustomBlockName,
          project_path: projectPath,
        }),
      });
      
      if (!response.ok) {
        const error = await response.json();
        const errorMessage = (error as any).detail || `Failed to create custom block (${response.status})`;
        console.error("Custom block creation failed:", errorMessage);
        throw new Error(errorMessage);
      }
      
      const blockDefinition = await response.json();
      return blockDefinition;
    } catch (error) {
      console.error("Error creating custom block:", error);
      // Re-throw to let the renderer handle the error properly
      throw error;
    }
  });
};

// Copyright (c) 2024 Emasoft (for atlasvibe modifications and derivative work)
// Copyright (c) 2024 Flojoy (for the original "Flojoy Studio" software)
//
// This software is licensed under the MIT License.
// Refer to the LICENSE file for more details.

import {
  app,
  BrowserWindow,
  shell,
  nativeImage,
  dialog,
  nativeTheme,
  ipcMain, // Added for handling custom events
} from "electron";
import { update } from "./update";
import log from "electron-log/main";
import { cleanup, isPortFree, killProcess } from "./utils";

import { is } from "@electron-toolkit/utils";

import { join } from "node:path";
import { DIST_ELECTRON, PUBLIC_DIR } from "./consts";

const getIcon = () => {
  switch (process.platform) {
    case "win32":
      return join(PUBLIC_DIR, "favicon.ico");
    case "linux":
      return join(PUBLIC_DIR, "favicon.png");
    default:
      return join(PUBLIC_DIR, "favicon.png");
  }
};

// Here, you can also use other preload
const preload = join(__dirname, `../preload/index.js`);

const devServerUrl = process.env["ELECTRON_RENDERER_URL"];
const indexHtml = join(DIST_ELECTRON, "renderer", "index.html");

export async function createWindow() {
  const mainWindow = new BrowserWindow({
    title: "atlasvibe",
    icon: getIcon(),
    autoHideMenuBar: true,
    titleBarStyle: process.platform === "darwin" ? "hidden" : "default",
    trafficLightPosition: {
      x: 15,
      y: 17, // macOS traffic lights seem to be 14px in diameter. If you want them vertically centered, set this to `titlebar_height / 2 - 7`.
    },
    webPreferences: {
      preload,
      sandbox: false,
    },
    minHeight: 680,
    minWidth: 1020,
    show: false,
  });
  global.mainWindow = mainWindow;
  global.hasUnsavedChanges = true;
  global.setupStarted = performance.now();

  mainWindow.on("ready-to-show", () => {
    mainWindow.show();
    mainWindow.maximize();
  });
  // setting icon for mac
  if (process.platform === "darwin") {
    app.dock.setIcon(nativeImage.createFromPath(getIcon()));
  }
  if (!(await isPortFree(5392))) {
    const choice = dialog.showMessageBoxSync(global.mainWindow, {
      type: "question",
      buttons: ["Exit", "Kill Process"],
      title: "Existing Server Detected",
      message:
        "Seems like there is already an atlasvibe server running! Do you want to kill it?",
      icon: getIcon(),
    });
    if (choice == 0) {
      mainWindow.destroy();
      app.quit();
      process.exit(0);
    } else {
      await killProcess(5392).catch((err) => log.error(err));
    }
  }
  if (!app.isPackaged && devServerUrl) {
    await mainWindow.loadURL(devServerUrl);
  } else {
    await mainWindow.loadFile(indexHtml);
  }

  mainWindow.on("close", (e) => {
    if (!global.hasUnsavedChanges) {
      return;
    }
    const choice = dialog.showMessageBoxSync(global.mainWindow, {
      type: "question",
      buttons: ["Yes", "No, go back"],
      title: "Quit?",
      message:
        "You have unsaved changes. Are you sure you want to quit atlasvibe?",
    });
    if (choice > 0) e.preventDefault();
  });

  // Make all links open with the browser, not with the application
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith("https:")) shell.openExternal(url);
    return { action: "deny" };
  });

  // Apply electron-updater
  update(cleanup);
}

const editorWindowMap: Map<string, BrowserWindow> = new Map();

export async function createEditorWindow(filepath: string) {
  let editorWindow = editorWindowMap.get(filepath);
  if (editorWindow) {
    if (editorWindow.isMinimized()) {
      editorWindow.restore();
    }
    editorWindow.focus();
    return;
  }

  // Create the browser window.
  editorWindow = new BrowserWindow({
    width: 900,
    height: 670,
    show: false,
    autoHideMenuBar: true,
    titleBarStyle: "hidden",
    backgroundColor: nativeTheme.shouldUseDarkColors ? "#000000" : "#ffffff",
    trafficLightPosition: {
      x: 15,
      y: 15, // macOS traffic lights seem to be 14px in diameter. If you want them vertically centered, set this to `titlebar_height / 2 - 7`.
    },
    icon: getIcon(),
    webPreferences: {
      preload: join(__dirname, "../preload/index.js"), // Ensure preload script is correctly path-ed
      sandbox: false,
      // Pass filepath to renderer process of editor window
      additionalArguments: [`--filepath=${filepath}`],
    },
  });

  editorWindow.on("ready-to-show", () => {
    if (editorWindow) {
      editorWindow.show();
    }
  });

  editorWindow.webContents.setWindowOpenHandler((details) => {
    shell.openExternal(details.url);
    return { action: "deny" };
  });

  // HMR for renderer base on electron-vite cli.
  // Load the remote URL for development or the local html file for production.
  if (is.dev && process.env["ELECTRON_RENDERER_URL"]) {
    editorWindow.loadURL(
      process.env["ELECTRON_RENDERER_URL"] + "#/editor/" + btoa(filepath),
    );
  } else {
    editorWindow.loadFile(indexHtml, {
      hash: "editor/" + btoa(filepath),
    });
  }

  // Task 2.5: In-IDE Block Code Editing and Synchronization
  // The editor window (if it's a custom editor implemented within Electron/Web tech)
  // would need to:
  // 1. Load the content of `filepath`.
  // 2. Provide editing capabilities.
  // 3. On save, use an IPC mechanism (e.g., `ipcRenderer.send('save-block-code', filepath, newContent)`)
  //    to send the new content to the main process.

  // Main process would handle 'save-block-code':
  // ipcMain.on('save-block-code', async (event, blockFilepath, content) => {
  //   try {
  //     await fs.promises.writeFile(blockFilepath, content);
  //     // After successful save, notify the backend to regenerate metadata for this block.
  //     // This requires another IPC call to the Python backend, possibly via the main window's renderer process
  //     // or a direct Python shell execution if the backend is structured to allow this.
  //     // Example: global.mainWindow.webContents.send('trigger-metadata-regeneration', blockFilepath);
  //     log.info(`Saved block code for: ${blockFilepath}`);
  //   } catch (error) {
  //     log.error(`Failed to save block code for ${blockFilepath}:`, error);
  //     // Optionally, send error back to editor window
  //   }
  // });
  // Note: Actual implementation of fs and IPC handlers requires more setup.

  app.on("before-quit", () => {
    if (editorWindow) {
      editorWindow.removeAllListeners("close");
    }
  });

  editorWindow.on("closed", () => {
    editorWindowMap.delete(filepath);
  });
}

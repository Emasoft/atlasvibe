// Copyright (c) 2024 Emasoft (for atlasvibe modifications and derivative work)
// Copyright (c) 2024 Flojoy (for the original "Flojoy Studio" software)
//
// This software is licensed under the MIT License.
// Refer to the LICENSE file for more details.

/* eslint-disable no-var */
import { BrowserWindow } from "electron";
// import api from "@/api/index"; // This line is problematic for global type declaration
import { InterpretersList } from "@/main/python/interpreter";
import { ChildProcess } from "child_process";
import { ExtendedWindowApi } from "./preload"; // Import the extended API type

declare global {
  // These are fine if they are truly global variables set up in your main process
  // and not part of the `window.api` bridge.
  var mainWindow: BrowserWindow;
  var pythonInterpreters: InterpretersList;
  var captainProcess: ChildProcess | null; // Consider renaming to atlasvibeEngineProcess
  var setupStarted: number;

  interface Window {
    api: ExtendedWindowApi; // Use the specific extended API type
  }
}

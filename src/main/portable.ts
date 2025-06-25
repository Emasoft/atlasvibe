/*
 * Portable mode detection and configuration
 */

import { app } from "electron";
import path from "path";
import fs from "fs";

export function setupPortableMode(): void {
  // Check if running in portable mode
  const isPortable =
    process.env.PORTABLE_MODE === "true" ||
    process.env.PORTABLE_EXECUTABLE_DIR ||
    checkPortableStructure();

  if (isPortable) {
    console.log("Running in portable mode");

    // Get the portable directory
    const portableDir =
      process.env.PORTABLE_EXECUTABLE_DIR ||
      path.dirname(path.dirname(app.getPath("exe")));

    // Override paths to use portable directories
    const userDataPath = path.join(portableDir, "userdata");
    const tempPath = path.join(portableDir, "temp");
    const cachePath = path.join(portableDir, "cache");

    // Create directories if they don't exist
    [userDataPath, tempPath, cachePath].forEach((dir) => {
      if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
      }
    });

    // Set Electron paths
    app.setPath("userData", userDataPath);
    app.setPath("temp", tempPath);
    app.setPath("cache", cachePath);

    // Set environment variable for backend
    process.env.ATLASVIBE_PORTABLE = "true";
    process.env.ATLASVIBE_ROOT = portableDir;

    console.log(`Portable paths configured:`);
    console.log(`  userData: ${userDataPath}`);
    console.log(`  temp: ${tempPath}`);
    console.log(`  cache: ${cachePath}`);
  }
}

function checkPortableStructure(): boolean {
  // Check if we're running from a typical portable structure
  const exePath = app.getPath("exe");
  const exeDir = path.dirname(exePath);

  // Look for portable markers
  const portableMarkers = [
    "AtlasVibe-Portable",
    "portable.txt",
    "../start-atlasvibe.bat",
    "../start-atlasvibe.sh",
  ];

  return portableMarkers.some((marker) => {
    const markerPath = path.join(exeDir, marker);
    return fs.existsSync(markerPath) || exeDir.includes(marker);
  });
}

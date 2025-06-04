import log from "electron-log/main";
import { execCommand } from "../executor";
import { app } from "electron";
import { Command } from "../command";
import { ChildProcess, execSync, spawn } from "child_process";
import { sendToStatusBar } from "../logging";
import {
  InterpretersList,
  PythonManager,
  interpreterCachePath,
} from "./interpreter";
import * as os from "os";
import { existsSync, mkdirSync, readFileSync } from "fs";
import { uvGroupEnsureValid } from "./uv";
import { store } from "../store";
import { join } from "path";

export async function checkPythonInstallation(
  _,
  force?: boolean,
): Promise<InterpretersList> {
  if (!global.pythonInterpreters || force) {
    // Check for virtual environment first
    if (process.env.VIRTUAL_ENV) {
      const venvPython = join(process.env.VIRTUAL_ENV, "bin", "python");
      if (existsSync(venvPython)) {
        try {
          const version = await PythonManager.getVersion(venvPython);
          if (version && (version.minor === 11 || version.minor === 12) && version.major === 3) {
            log.info(`Using Python from VIRTUAL_ENV: ${venvPython}`);
            global.pythonInterpreters = [{
              path: venvPython,
              version,
              default: true,
            }];
            // Also add other discovered interpreters but not as default
            const py311 = await new PythonManager().getInterpreterByVersion({
              major: 3,
              minor: 11,
            });
            const py312 = await new PythonManager().getInterpreterByVersion({
              major: 3,
              minor: 12,
            });
            global.pythonInterpreters.push(...py311.filter(i => i.path !== venvPython), ...py312.filter(i => i.path !== venvPython));
            return global.pythonInterpreters;
          }
        } catch (err) {
          log.warn(`Failed to use VIRTUAL_ENV Python: ${err}`);
        }
      }
    }
    
    const py311 = await new PythonManager().getInterpreterByVersion({
      major: 3,
      minor: 11,
    });
    const py312 = await new PythonManager().getInterpreterByVersion({
      major: 3,
      minor: 12,
    });
    global.pythonInterpreters = [...py311, ...py312];
  }
  if (existsSync(interpreterCachePath)) {
    const interpreter = readFileSync(interpreterCachePath).toString("utf-8");
    const matchedVersion11 = await PythonManager.checkVersion(interpreter, {
      major: 3,
      minor: 11,
    });
    const matchedVersion12 = await PythonManager.checkVersion(interpreter, {
      major: 3,
      minor: 12,
    });
    const matchedVersion = matchedVersion11 || matchedVersion12;
    if (matchedVersion) {
      const foundInterpreterInList = global.pythonInterpreters.find(
        (i) => i.path === interpreter,
      );
      if (foundInterpreterInList) {
        global.pythonInterpreters = global.pythonInterpreters.map((i) => ({
          ...i,
          default: i.path === interpreter ? true : false,
        }));
      } else {
        const version = await PythonManager.getVersion(interpreter);
        if (version) {
          global.pythonInterpreters.push({
            path: interpreter,
            version,
            default: true,
          });
        }
      }
    }
  }
  return global.pythonInterpreters;
}

export async function installUv(): Promise<string> {
  // UV is typically installed globally, not via pip
  // Check if uv is already available
  try {
    await execCommand(new Command("uv --version"), { quiet: true });
    return "uv is already installed";
  } catch {
    // Install uv using the official installer
    return await execCommand(
      new Command({
        darwin: "curl -LsSf https://astral.sh/uv/install.sh | sh",
        win32: "powershell -c \"irm https://astral.sh/uv/install.ps1 | iex\"",
        linux: "curl -LsSf https://astral.sh/uv/install.sh | sh",
      }),
    );
  }
}

export async function uvEnsurepath(): Promise<void> {
  // UV typically adds itself to PATH during installation
  // But we can ensure ~/.local/bin is in PATH
  const uvBinPath = join(os.homedir(), ".local", "bin");
  const existingPaths = process.env.PATH;

  log.info("uvEnsurepath: " + uvBinPath);
  log.info("existingPaths: " + existingPaths);

  if (!existingPaths?.includes(uvBinPath)) {
    process.env.PATH = `${uvBinPath}:${existingPaths}`;
  }
}

export async function ensureUvEnvironment(): Promise<void> {
  // Ensure UV is available and environment is set up
  try {
    await execCommand(new Command("uv --version"), { quiet: true });
  } catch {
    await installUv();
  }
  
  // Ensure virtual environment exists
  const venvPath = join(app.isPackaged ? process.resourcesPath! : process.cwd(), ".venv");
  if (!existsSync(venvPath)) {
    log.info("Creating virtual environment with uv...");
    await execCommand(new Command("uv venv --python 3.11"));
  }
  
  // Set UV_PYTHON to use the venv
  process.env.UV_PYTHON = join(venvPath, "bin", "python");
  process.env.VIRTUAL_ENV = venvPath;
}

export async function installDependencies(): Promise<string> {
  // Ensure we're in a virtual environment
  await ensureUvEnvironment();
  
  const validGroups = await uvGroupEnsureValid();
  if (validGroups.length > 0) {
    const extras = validGroups.map(g => `[${g}]`).join("");
    return await execCommand(
      new Command(`uv pip install -e .${extras}`),
    );
  }
  return await execCommand(new Command(`uv pip install -e .`));
}

export async function spawnCaptain(): Promise<void> {
  return new Promise((_, reject) => {
    // If we're in a virtual environment, use python directly
    let pythonCommand = "python";
    if (process.env.VIRTUAL_ENV) {
      pythonCommand = join(process.env.VIRTUAL_ENV, "bin", "python");
    } else if (process.env.PY_INTERPRETER) {
      pythonCommand = process.env.PY_INTERPRETER;
    }
    
    const command = new Command(`"${pythonCommand}" main.py`);

    log.info("execCommand: " + command.getCommand());
    log.info("Working directory: " + (app.isPackaged ? process.resourcesPath : process.cwd()));

    global.captainProcess = spawn(
      command.getCommand().split(" ")[0],
      command.getCommand().split(" ").slice(1),
      {
        cwd: app.isPackaged ? process.resourcesPath : undefined,
        shell: true,
        env: {
          ...process.env,
          LOCAL_DB_PATH: store.path,
          PYTHONPATH: process.env.PYTHONPATH || "",
        },
      },
    );

    global.captainProcess.stdout?.on("data", (data) => {
      log.info(data.toString());
      sendToStatusBar(data.toString());
    });

    global.captainProcess.stderr?.on("data", (data) => {
      log.error(data.toString());
      sendToStatusBar(data.toString());
    });

    global.captainProcess.on("error", (error) => {
      log.error(error.message);
      sendToStatusBar(error.message);
    });

    global.captainProcess.on("exit", (code) => {
      if (code !== 0 && !global?.mainWindow?.isDestroyed()) {
        reject("Captain process is exited with code " + code);
      }
    });
  });
}

export function killCaptain(): boolean {
  if (process.platform === "win32") {
    try {
      execSync(
        `taskkill -F -T -PID ${(global.captainProcess as ChildProcess).pid}`,
      );
      return true;
    } catch (err) {
      log.error(err);
      return false;
    }
  }
  return (global.captainProcess as ChildProcess).kill();
}

export async function listPythonPackages() {
  return await execCommand(new Command(`uv pip freeze`), {
    quiet: true,
  });
}

export async function pyvisaInfo() {
  return await execCommand(new Command(`uv run pyvisa-info`), {
    quiet: true,
  });
}

const getUvPath = async () => {
  const localBinPath = join(os.homedir(), ".local", "bin", "uv");
  try {
    await execCommand(new Command(`${localBinPath} --version`), { quiet: true });
    return localBinPath;
  } catch (error) {
    return "uv";
  }
};

export async function restartCaptain() {
  if (!global.captainProcess?.killed) {
    const killed = global.captainProcess?.kill();
    while (!killed) {
      continue;
    }
  }
  await spawnCaptain();
}

#!/usr/bin/env node
// -*- coding: utf-8 -*-

// HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
// - New file to replace Poetry functionality with uv
// - Implements all Poetry commands using uv equivalents
// 

import { PoetryGroupInfo, PythonDependency } from "src/types/poetry";
import { Command } from "../command";
import { execCommand } from "../executor";
import pyproject from "../../../pyproject.toml?raw";
import toml from "toml";
import { store } from "../store";
import * as fs from "fs";
import log from "electron-log/main";

// UV dependency groups (same as Poetry groups for compatibility)
export const UV_DEP_GROUPS: Pick<
  PoetryGroupInfo,
  "name" | "description"
>[] = [
  {
    name: "blocks",
    description: "Core dependencies for Atlasvibe Blocks",
  },
  {
    name: "dev",
    description: "Development dependencies for Atlasvibe Studio",
  },
  {
    name: "ai-ml",
    description: "AI and Machine Learning dependencies",
  },
  {
    name: "hardware",
    description: "Hardware dependencies",
  },
  {
    name: "user",
    description: "User dependencies",
  },
];

function processUvList(stdout: string): PythonDependency[] {
  return stdout.split("\n").filter(line => line.trim()).map((line) => {
    // UV pip list format: package-name==version
    const match = line.match(/^(.+?)==(.+?)$/);
    if (match) {
      return {
        name: match[1],
        version: match[2],
        description: "", // UV doesn't provide descriptions in list output
        installed: true,
      };
    }
    return {
      name: line,
      version: "unknown",
      description: "",
      installed: false,
    };
  });
}

export async function uvShowTopLevel(): Promise<PythonDependency[]> {
  // UV doesn't have a direct equivalent to poetry show --top-level
  // We'll use pip list instead
  const stdout = await execCommand(
    new Command(`uv pip list`),
    { quiet: true }
  );
  return processUvList(stdout);
}

export async function uvShowUserGroup(): Promise<PythonDependency[]> {
  // For user group, we'll read from pyproject.toml and check what's installed
  const installed = await uvShowTopLevel();
  const parsed = toml.parse(pyproject);
  
  if (parsed?.project?.["optional-dependencies"]?.user) {
    const userDeps = parsed.project["optional-dependencies"].user;
    return userDeps.map((dep: string) => {
      const match = dep.match(/^(.+?)([><=~!]+.+)?$/);
      const name = match ? match[1] : dep;
      const installedDep = installed.find(d => d.name === name);
      return {
        name,
        version: installedDep?.version || "not installed",
        description: "",
        installed: !!installedDep,
      };
    });
  }
  
  return [];
}

export async function uvGetGroupInfo(): Promise<PoetryGroupInfo[]> {
  const installed = await uvShowTopLevel();
  const parsed = toml.parse(pyproject);
  
  const result: PoetryGroupInfo[] = [];
  
  // Check optional-dependencies (uv style)
  if (parsed?.project?.["optional-dependencies"]) {
    Object.entries(parsed.project["optional-dependencies"]).forEach(([key, deps]) => {
      if (key !== "user") {
        const dependencies = (deps as string[]).map((dep: string) => {
          const match = dep.match(/^(.+?)([><=~!]+.+)?$/);
          const name = match ? match[1] : dep;
          const version = match && match[2] ? match[2] : "*";
          const installedDep = installed.find(d => d.name === name);
          
          return {
            name,
            version,
            installed: !!installedDep,
          };
        });
        
        result.push({
          name: key,
          dependencies,
          description:
            UV_DEP_GROUPS.find((group) => group.name === key)?.description ??
            "Unknown",
          status: dependencies.every((dep) => dep.installed)
            ? "installed"
            : "dne",
        });
      }
    });
  }
  
  return result;
}

export async function uvGroupEnsureValid(): Promise<string[]> {
  const groups = store.get("poetryOptionalGroups"); // Keep same store key for compatibility
  
  // make sure the group actually exists
  const validGroups = groups.filter((group) =>
    UV_DEP_GROUPS.find((g) => g.name === group),
  );
  store.set("poetryOptionalGroups", validGroups);
  return validGroups;
}

export async function uvInstallDepGroup(group: string): Promise<boolean> {
  if (group !== "blocks") {
    const groups = store.get("poetryOptionalGroups");
    if (!groups.includes(group)) {
      store.set("poetryOptionalGroups", [...groups, group]);
    }
  }

  const validGroups = await uvGroupEnsureValid();
  
  // UV installs optional dependencies differently
  // We need to install with extras
  if (validGroups.length > 0) {
    const extras = validGroups.map(g => `[${g}]`).join("");
    await execCommand(
      new Command(`uv pip install -e .${extras}`),
    );
  } else {
    await execCommand(new Command(`uv pip install -e .`));
  }

  return true;
}

export async function uvInstallDepUserGroup(
  name: string,
): Promise<boolean> {
  const groups = store.get("poetryOptionalGroups");
  if (!groups.includes("user")) {
    store.set("poetryOptionalGroups", [...groups, "user"]);
  }
  
  // UV doesn't have groups like Poetry, so we install directly
  await execCommand(new Command(`uv pip install ${name}`));
  
  // TODO: Update pyproject.toml to add to user group
  // This would require modifying the pyproject.toml file
  
  return true;
}

export async function uvInstallRequirementsUserGroup(
  filePath: string,
): Promise<boolean> {
  try {
    // UV can install from requirements file directly
    await execCommand(new Command(`uv pip install -r ${filePath}`));
    return true;
  } catch (e) {
    log.info(e);
    return false;
  }
}

export async function uvUninstallDepUserGroup(
  name: string,
): Promise<boolean> {
  await execCommand(new Command(`uv pip uninstall ${name} -y`));
  
  // Reinstall with current groups
  const validGroups = await uvGroupEnsureValid();
  if (validGroups.length > 0) {
    const extras = validGroups.map(g => `[${g}]`).join("");
    await execCommand(new Command(`uv pip install -e .${extras}`));
  }
  
  return true;
}

export async function uvUninstallDepGroup(group: string): Promise<boolean> {
  if (group !== "blocks") {
    const groups = store.get("poetryOptionalGroups");
    const newGroups = groups.filter((g: string) => g !== group);
    store.set("poetryOptionalGroups", newGroups);
  }

  const validGroups = await uvGroupEnsureValid();
  
  // Reinstall with remaining groups
  if (validGroups.length > 0) {
    const extras = validGroups.map(g => `[${g}]`).join("");
    await execCommand(new Command(`uv pip install -e .${extras}`));
  } else {
    await execCommand(new Command(`uv pip install -e .`));
  }

  return true;
}
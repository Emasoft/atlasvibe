/*
 * Copyright (c) 2024 Emasoft
 *
 * This file is part of AtlasVibe, which is based on Flojoy Studio
 * Original Copyright (c) 2023-2024 Flojoy
 *
 * SPDX-License-Identifier: MIT
 * See the LICENSE file for details.
 */

// HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
// - Completely rewritten to remove all Poetry and store references
// - Now uses uv commands directly without legacy store management
// - Types renamed from Poetry-specific to generic dependency management
//

// UV package management utilities
// This replaces the legacy Poetry functionality

import { Command } from "@/main/command";
import { execCommand } from "@/main/executor";
import * as TOML from "@iarna/toml";
import * as fs from "fs";
import * as path from "path";
import log from "electron-log/main";
import { DependencyGroupInfo, PythonDependency } from "@/types/dependencies";

interface PyProjectToml {
  project?: {
    dependencies?: string[];
    "optional-dependencies"?: {
      [key: string]: string[];
    };
    name?: string;
    version?: string;
    description?: string;
    requires?: string[];
  };
  "dependency-groups"?: {
    [key: string]: string[];
  };
  tool?: {
    [key: string]: unknown;
  };
  "build-system"?: {
    requires?: string[];
    "build-backend"?: string;
  };
}

// UV dependency groups
export const UV_DEP_GROUPS: Pick<
  DependencyGroupInfo,
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
  return stdout
    .split("\n")
    .filter((line) => line.trim())
    .map((line) => {
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
  const stdout = await execCommand(new Command(`uv pip list`), { quiet: true });
  return processUvList(stdout);
}

export async function uvShowUserGroup(): Promise<PythonDependency[]> {
  // For user group, we'll read from pyproject.toml and check what's installed
  const installed = await uvShowTopLevel();
  const pyprojectPath = path.join(process.cwd(), "pyproject.toml");
  const pyprojectContent = fs.readFileSync(pyprojectPath, "utf8");
  const parsed = TOML.parse(pyprojectContent) as PyProjectToml;

  if (parsed?.project?.["optional-dependencies"]?.user) {
    const userDeps = parsed.project["optional-dependencies"].user;
    return userDeps.map((dep: string) => {
      const match = dep.match(/^(.+?)([><=~!]+.+)?$/);
      const name = match ? match[1] : dep;
      const installedDep = installed.find((d) => d.name === name);
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

export async function uvGetGroupInfo(): Promise<DependencyGroupInfo[]> {
  const installed = await uvShowTopLevel();
  const pyprojectPath = path.join(process.cwd(), "pyproject.toml");
  const pyprojectContent = fs.readFileSync(pyprojectPath, "utf8");
  const parsed = TOML.parse(pyprojectContent) as PyProjectToml;

  const result: DependencyGroupInfo[] = [];

  // Check optional-dependencies (uv style)
  if (parsed?.project?.["optional-dependencies"]) {
    Object.entries(parsed.project["optional-dependencies"]).forEach(
      ([key, deps]) => {
        if (key !== "user") {
          const dependencies = (deps as string[]).map((dep: string) => {
            const match = dep.match(/^(.+?)([><=~!]+.+)?$/);
            const name = match ? match[1] : dep;
            const version = match && match[2] ? match[2] : "*";
            const installedDep = installed.find((d) => d.name === name);

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
      },
    );
  }

  return result;
}

// Get currently installed optional groups from pyproject.toml
export async function uvGetInstalledGroups(): Promise<string[]> {
  const pyprojectPath = "pyproject.toml";
  try {
    const content = fs.readFileSync(pyprojectPath, "utf8");
    const parsed = TOML.parse(content) as unknown as PyProjectToml;

    // Get all available optional dependency groups
    if (parsed?.project?.["optional-dependencies"]) {
      const groups = Object.keys(parsed.project["optional-dependencies"]);
      return groups.filter((group) =>
        UV_DEP_GROUPS.find((g) => g.name === group),
      );
    }
  } catch (e) {
    log.error("Failed to read installed groups:", e);
  }
  return [];
}

export async function uvInstallDepGroup(group: string): Promise<boolean> {
  // Install the specific group using uv
  try {
    await execCommand(new Command(`uv pip install -e .[${group}]`));
    return true;
  } catch (e) {
    log.error(`Failed to install group ${group}:`, e);
    return false;
  }
}

export async function uvInstallDepUserGroup(name: string): Promise<boolean> {
  // Install the dependency directly
  await execCommand(new Command(`uv pip install ${name}`));

  // Update pyproject.toml to add to user group
  const pyprojectPath = "pyproject.toml";
  try {
    const pyprojectContent = fs.readFileSync(pyprojectPath, "utf8");
    const parsed = TOML.parse(pyprojectContent) as unknown as PyProjectToml;

    // Ensure optional-dependencies exists
    if (!parsed.project) {
      parsed.project = {};
    }
    if (!parsed.project["optional-dependencies"]) {
      parsed.project["optional-dependencies"] = {};
    }
    if (!parsed.project["optional-dependencies"].user) {
      parsed.project["optional-dependencies"].user = [];
    }

    // Add the dependency if it doesn't exist
    const userDeps = parsed.project["optional-dependencies"].user as string[];
    if (!userDeps.some((dep) => dep.startsWith(name))) {
      userDeps.push(name);

      // Write back to file
      const tomlContent = TOML.stringify(parsed as unknown as TOML.JsonMap);
      fs.writeFileSync(pyprojectPath, tomlContent, "utf8");
      log.info(`Added ${name} to user dependencies in pyproject.toml`);
    }

    // Install with the user group
    await execCommand(new Command(`uv pip install -e .[user]`));
  } catch (e) {
    log.error("Failed to update pyproject.toml:", e);
    return false;
  }

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

export async function uvUninstallDepUserGroup(name: string): Promise<boolean> {
  // Uninstall the specific package
  await execCommand(new Command(`uv pip uninstall ${name} -y`));

  // Remove from pyproject.toml
  const pyprojectPath = "pyproject.toml";
  try {
    const pyprojectContent = fs.readFileSync(pyprojectPath, "utf8");
    const parsed = TOML.parse(pyprojectContent) as unknown as PyProjectToml;

    if (parsed?.project?.["optional-dependencies"]?.user) {
      const userDeps = parsed.project["optional-dependencies"].user as string[];
      const filtered = userDeps.filter((dep) => !dep.startsWith(name));

      if (filtered.length !== userDeps.length) {
        parsed.project["optional-dependencies"].user = filtered;
        const tomlContent = TOML.stringify(parsed as unknown as TOML.JsonMap);
        fs.writeFileSync(pyprojectPath, tomlContent, "utf8");
        log.info(`Removed ${name} from user dependencies in pyproject.toml`);
      }
    }
  } catch (e) {
    log.error("Failed to update pyproject.toml:", e);
    return false;
  }

  return true;
}

export async function uvUninstallDepGroup(group: string): Promise<boolean> {
  // There's no direct way to "uninstall" a group in uv/pip
  // We would need to uninstall individual packages from that group
  // For now, just log a warning
  log.warn(
    `Group uninstallation not directly supported. Please uninstall individual packages from group '${group}'.`,
  );
  return true;
}

// Ensure valid optional dependency groups exist in pyproject.toml
export async function uvGroupEnsureValid(): Promise<string[]> {
  const pyprojectPath = "pyproject.toml";
  const validGroups: string[] = [];

  try {
    if (!fs.existsSync(pyprojectPath)) {
      log.warn("pyproject.toml not found");
      return validGroups;
    }

    const content = fs.readFileSync(pyprojectPath, "utf8");
    const parsed = TOML.parse(content) as unknown as PyProjectToml;

    // Check for optional-dependencies (uv style)
    if (parsed?.project?.["optional-dependencies"]) {
      const optionalDeps = parsed.project["optional-dependencies"];
      for (const [groupName, deps] of Object.entries(optionalDeps)) {
        // Only include groups that have dependencies defined
        if (Array.isArray(deps) && deps.length > 0) {
          validGroups.push(groupName);
        }
      }
    }

    // Check for dependency-groups (new uv style)
    if (parsed?.["dependency-groups"]) {
      const depGroups = parsed["dependency-groups"];
      for (const [groupName, deps] of Object.entries(depGroups)) {
        // Only include groups that have dependencies defined
        if (
          Array.isArray(deps) &&
          deps.length > 0 &&
          !validGroups.includes(groupName)
        ) {
          validGroups.push(groupName);
        }
      }
    }

    log.info(`Found valid dependency groups: ${validGroups.join(", ")}`);
    return validGroups;
  } catch (error) {
    log.error(`Error reading pyproject.toml: ${error}`);
    return validGroups;
  }
}

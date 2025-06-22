/*
 * Copyright (c) 2024 Emasoft
 *
 * This file is part of AtlasVibe, which is based on Flojoy Studio
 * Original Copyright (c) 2023-2024 Flojoy
 *
 * SPDX-License-Identifier: MIT
 * See the LICENSE file for details.
 */

/**
 * Gallery loader for the new folder-based sample projects.
 * Loads sample projects from the migrated folder structure.
 */

import { Project } from "@/renderer/types/project";
import { Result, ok, err } from "neverthrow";

/**
 * Load a sample project from the new folder-based structure
 * @param projectName Name of the sample project
 * @returns Project data or error
 */
export async function loadSampleProject(
  projectName: string,
): Promise<Result<Project, Error>> {
  try {
    // Sample projects are now in sample_projects/<name>/<name>.atlasvibe
    const projectPath = `sample_projects/${projectName}/${projectName}.atlasvibe`;

    // In Electron, we need to load these from the app resources
    // The window.api should provide a way to load these bundled files
    const fileContent = await window.api.loadFileFromFullPath(projectPath);

    if (!fileContent) {
      return err(new Error(`Sample project ${projectName} not found`));
    }

    const projectData = JSON.parse(fileContent) as Project;

    // The project data should already be in the new format with custom blocks
    // Check if it needs migration (shouldn't happen for pre-migrated samples)
    if (!projectData.version || projectData.version === "1.0.0") {
      return err(
        new Error(
          `Sample project ${projectName} is in old format. Please run migration.`,
        ),
      );
    }

    return ok(projectData);
  } catch (error) {
    return err(error as Error);
  }
}

/**
 * Get the full path to a sample project
 * @param projectName Name of the sample project
 * @returns Full path to the project file
 */
export function getSampleProjectPath(projectName: string): string {
  return `sample_projects/${projectName}/${projectName}.atlasvibe`;
}

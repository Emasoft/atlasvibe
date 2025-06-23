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
// - New file for project file format migration
// - Handles backward compatibility with old project formats
// - Ensures custom blocks are properly identified
//

import { Project } from "@/renderer/types/project";
import { Node, Edge } from "reactflow";
import { BlockData } from "@/renderer/types/block";

export interface ProjectMigrationResult {
  project: Project;
  version: string;
  migrated: boolean;
}

/**
 * Migrates project files to the latest format
 * Ensures custom blocks have proper path references
 */
export function migrateProjectFormat(
  projectData: unknown,
): ProjectMigrationResult {
  // Type guard to ensure projectData is an object
  if (!projectData || typeof projectData !== "object") {
    throw new Error("Invalid project data");
  }

  const data = projectData as Record<string, unknown>;

  let migrated = false;
  const project = { ...data } as Record<string, unknown>;

  // Migrate from v1 to v2 format (add custom block support)
  if (!project.version || project.version === "1.0.0") {
    migrated = true;
    project.version = "2.0.0";

    // Check each node to see if it might be a custom block
    const rfInstance = project.rfInstance as
      | {
          nodes?: Node<BlockData>[];
          edges?: Edge[];
        }
      | undefined;
    if (rfInstance?.nodes) {
      rfInstance.nodes = rfInstance.nodes.map((node: Node<BlockData>) => {
        // If node already has isCustom flag and path, preserve it
        if (node.data.isCustom !== undefined && node.data.path) {
          return node;
        }

        // ALL blocks in workflows are custom blocks by definition!
        // They are instances copied from blueprints and are editable
        return {
          ...node,
          data: {
            ...node.data,
            isCustom: true,
            // Generate path from function name if not present
            // Use the block's func name which includes the instance suffix (e.g. FFT_1)
            path: node.data.path || `atlasvibe_blocks/${node.data.func}`,
          },
        };
      });
    }
  }

  return {
    project: project as Project,
    version: (project.version as string) || "2.0.0",
    migrated,
  };
}

/**
 * Validates that all custom blocks have proper references
 */
export function validateProjectReferences(project: Project): string[] {
  const errors: string[] = [];

  project.rfInstance.nodes.forEach((node, index) => {
    if (node.data.isCustom) {
      if (!node.data.path) {
        errors.push(
          `Custom block at index ${index} (${node.data.func}) is missing path reference`,
        );
      } else if (!node.data.path.includes("atlasvibe_blocks/")) {
        errors.push(
          `Custom block at index ${index} (${node.data.func}) has invalid path: ${node.data.path}`,
        );
      }
    }
  });

  return errors;
}

/**
 * Updates custom block references when project is moved or renamed
 */
export function updateCustomBlockPaths(project: Project): Project {
  // Since paths are relative to the project directory,
  // they don't need updating when the project moves
  // This function is here for future compatibility if we switch to absolute paths

  // Clone the project to avoid mutations
  const updatedProject = JSON.parse(JSON.stringify(project)) as Project;

  // If we ever use absolute paths, the logic would be:
  // updatedProject.rfInstance.nodes = updatedProject.rfInstance.nodes.map(node => {
  //   if (node.data.isCustom && node.data.path) {
  //     // Replace old project path with new one
  //     node.data.path = node.data.path.replace(oldProjectPath, newProjectPath);
  //   }
  //   return node;
  // });

  return updatedProject;
}

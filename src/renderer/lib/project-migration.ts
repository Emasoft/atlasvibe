#!/usr/bin/env node
// -*- coding: utf-8 -*-

// HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
// - New file for project file format migration
// - Handles backward compatibility with old project formats
// - Ensures custom blocks are properly identified
// 

import { Project } from '@/renderer/types/project';
import { Node } from 'reactflow';
import { BlockData } from '@/renderer/types/block';

export interface ProjectMigrationResult {
  project: Project;
  version: string;
  migrated: boolean;
}

/**
 * Migrates project files to the latest format
 * Ensures custom blocks have proper path references
 */
export function migrateProjectFormat(projectData: any): ProjectMigrationResult {
  // Detect version (old projects don't have version field)
  const version = projectData.version || '1.0.0';
  
  let migrated = false;
  const project = { ...projectData };

  // Migrate from v1 to v2 format (add custom block support)
  if (!project.version || project.version === '1.0.0') {
    migrated = true;
    project.version = '2.0.0';
    
    // Check each node to see if it might be a custom block
    if (project.rfInstance?.nodes) {
      project.rfInstance.nodes = project.rfInstance.nodes.map((node: Node<BlockData>) => {
        // If node already has isCustom flag, preserve it
        if (node.data.isCustom !== undefined) {
          return node;
        }
        
        // Try to detect custom blocks by checking if they're not in standard blocks
        // This is a heuristic - in v1 we didn't track custom blocks properly
        const isLikelyCustom = detectIfCustomBlock(node);
        
        if (isLikelyCustom) {
          return {
            ...node,
            data: {
              ...node.data,
              isCustom: true,
              // Generate path from function name if not present
              path: node.data.path || `atlasvibe_blocks/${node.data.func}`,
            },
          };
        }
        
        return node;
      });
    }
  }

  return {
    project: project as Project,
    version: project.version || '2.0.0',
    migrated,
  };
}

/**
 * Heuristic to detect if a block might be custom
 * This is used for migrating old projects that didn't track custom blocks
 */
function detectIfCustomBlock(node: Node<BlockData>): boolean {
  const func = node.data.func;
  
  // If it has a path already, it's definitely custom
  if (node.data.path && node.data.path.includes('atlasvibe_blocks/')) {
    return true;
  }
  
  // Check for common patterns in standard blocks
  // Standard blocks typically have ALL_CAPS names with underscores
  // and belong to known categories
  const standardPatterns = [
    // Math operations
    /^(ADD|SUBTRACT|MULTIPLY|DIVIDE|POWER|LOG|ABS|FLOOR_DIVIDE|REMAINDER)$/,
    // Trigonometry
    /^(SINE|COSINE|TANGENT|ARCSINE|ARCCOSINE|ARCTANGENT)$/,
    // Constants and generators
    /^(CONSTANT|LINSPACE|LOGSPACE|ARANGE|ZEROS|ONES)$/,
    // Signal processing
    /^(FFT|IFFT|FILTER|BUTTER|FIR|SAVGOL|PID)$/,
    // Data structures
    /^(MATRIX|VECTOR|SCALAR|DATAFRAME)$/,
    // Visualization
    /^(PLOT|IMAGE|TEXT|HISTOGRAM|SCATTER)$/,
    // I/O
    /^(IMPORT_|EXPORT_|LOAD_|SAVE_)/,
    // Control flow
    /^(LOOP|CONDITIONAL|TIMER|APPEND|BREAK)$/,
    // Hardware/devices
    /^(ARDUINO|LABJACK|OSCILLOSCOPE|DMM|CAMERA)/,
  ];
  
  // If it matches any standard pattern, it's not custom
  const isStandard = standardPatterns.some(pattern => pattern.test(func));
  
  // Additional check: custom blocks often have project-specific names
  // that don't follow the ALL_CAPS_WITH_UNDERSCORES convention
  const hasNonStandardNaming = !(/^[A-Z][A-Z0-9_]*$/.test(func));
  
  return !isStandard || hasNonStandardNaming;
}

/**
 * Validates that all custom blocks have proper references
 */
export function validateProjectReferences(project: Project): string[] {
  const errors: string[] = [];
  
  project.rfInstance.nodes.forEach((node, index) => {
    if (node.data.isCustom) {
      if (!node.data.path) {
        errors.push(`Custom block at index ${index} (${node.data.func}) is missing path reference`);
      } else if (!node.data.path.includes('atlasvibe_blocks/')) {
        errors.push(`Custom block at index ${index} (${node.data.func}) has invalid path: ${node.data.path}`);
      }
    }
  });
  
  return errors;
}

/**
 * Updates custom block references when project is moved or renamed
 */
export function updateCustomBlockPaths(
  project: Project,
  oldProjectPath: string,
  newProjectPath: string
): Project {
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
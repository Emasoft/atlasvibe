#!/usr/bin/env node
// -*- coding: utf-8 -*-

// HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
// - New file defining types for custom blocks
// - Extends BlockDefinition with path and isCustom properties
// - Provides type safety for custom block operations
// 

import { BlockDefinition } from '@/renderer/types/manifest';

/**
 * Extended block definition for custom blocks
 * Includes path reference to the block's location in project
 */
export interface CustomBlockDefinition extends BlockDefinition {
  /** Relative path to the custom block in the project */
  path: string;
  /** Flag indicating this is a custom block */
  isCustom: boolean;
}

/**
 * Response type from createCustomBlockFromBlueprint API
 */
export interface CreateCustomBlockResponse {
  blockDefinition: CustomBlockDefinition;
  blockPath: string;
}
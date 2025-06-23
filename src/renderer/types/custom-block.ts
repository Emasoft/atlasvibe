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

/**
 * Response type from updateBlockCode API
 */
export interface UpdateBlockCodeResponse {
  transaction_id: string;
  block_id: string;
  block_name: string;
  path: string;
  has_pending_changes: boolean;
  is_executing: boolean;
  version: number;
  status: 'queued' | 'applied';
}

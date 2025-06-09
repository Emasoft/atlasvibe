#!/usr/bin/env node
// -*- coding: utf-8 -*-

// HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
// - New file for creating nodes with consistent logic
// - Extracts duplicated node creation code into reusable functions
// - Handles both standard and custom blocks
// 

import { Node, XYPosition } from 'reactflow';
import { v4 as uuidv4 } from 'uuid';
import { BlockDefinition } from '@/renderer/types/manifest';
import { BlockData } from '@/renderer/stores/project';
import { DeviceInfo } from '@/renderer/types/hardware';
import { 
  createBlockId, 
  createBlockLabel, 
  ctrlsFromParams,
  addRandomPositionOffset 
} from '@/renderer/lib/block';

export interface CreateNodeOptions {
  /** Block definition (standard or custom) */
  blockDefinition: BlockDefinition;
  /** Position for the new node */
  position: XYPosition;
  /** Optional custom label */
  label?: string;
  /** Hardware devices for parameter initialization */
  hardwareDevices?: DeviceInfo;
  /** Taken node labels for unique naming */
  takenLabels?: RegExpMatchArray[];
  /** Whether this is a custom block */
  isCustom?: boolean;
  /** Path to custom block (required if isCustom is true) */
  customPath?: string;
}

/**
 * Creates a new node from a block definition
 * Handles both standard and custom blocks
 */
export function createNodeFromBlock(options: CreateNodeOptions): Node<BlockData> {
  const {
    blockDefinition,
    position,
    label: customLabel,
    hardwareDevices,
    takenLabels = [],
    isCustom = false,
    customPath
  } = options;

  const {
    key: funcName,
    type,
    parameters: params,
    init_parameters: initParams,
    inputs,
    outputs,
    pip_dependencies,
  } = blockDefinition;

  const nodeId = createBlockId(funcName);
  
  // Determine label
  let nodeLabel = customLabel;
  if (!nodeLabel) {
    if (funcName === "CONSTANT" && params?.["constant"]) {
      nodeLabel = params["constant"].default?.toString();
    } else {
      nodeLabel = createBlockLabel(funcName, takenLabels);
    }
  }

  const nodeCtrls = ctrlsFromParams(params, funcName, hardwareDevices);
  const initCtrls = ctrlsFromParams(initParams, funcName);

  const nodeData: BlockData = {
    id: nodeId,
    label: nodeLabel ?? funcName,
    func: funcName,
    type,
    ctrls: nodeCtrls,
    initCtrls: initCtrls,
    inputs,
    outputs,
    pip_dependencies,
  };

  // Add custom block properties if applicable
  if (isCustom) {
    if (!customPath) {
      throw new Error('Custom blocks must have a path');
    }
    nodeData.path = customPath;
    nodeData.isCustom = true;
  }

  return {
    id: nodeId,
    type,
    data: nodeData,
    position,
  };
}

/**
 * Creates a duplicate of an existing node
 * Handles position offset and label generation
 */
export function duplicateNode(
  originalNode: Node<BlockData>, 
  takenLabels: RegExpMatchArray[]
): Node<BlockData> {
  const funcName = originalNode.data.func;
  const id = createBlockId(funcName);

  const newLabel = originalNode.data.func === "CONSTANT"
    ? originalNode.data.ctrls["constant"].value!.toString()
    : createBlockLabel(funcName, takenLabels);

  const newNode: Node<BlockData> = {
    ...originalNode,
    id,
    data: {
      ...originalNode.data,
      id,
      label: newLabel,
    },
    position: {
      x: originalNode.position.x + 30,
      y: originalNode.position.y + 30,
    },
    selected: true,
  };

  return newNode;
}
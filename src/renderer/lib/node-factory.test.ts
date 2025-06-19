#!/usr/bin/env node
// -*- coding: utf-8 -*-

// HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
// - New test file for node factory functions
// - Tests for creating nodes from block definitions
// - Tests for duplicating nodes with proper label generation
//

import { describe, it, expect, vi } from 'vitest';
import { createNodeFromBlock, duplicateNode, CreateNodeOptions } from './node-factory';
import { BlockDefinition } from '@/renderer/types/manifest';
import { Node } from 'reactflow';
import { BlockData } from '@/renderer/stores/project';

// Mock the block utility functions
vi.mock('@/renderer/lib/block', () => ({
  createBlockId: vi.fn((func: string) => `${func}-${Date.now()}`),
  createBlockLabel: vi.fn((func: string, taken: any[]) => `${func} ${taken.length + 1}`),
  ctrlsFromParams: vi.fn((params: any) => params || {}),
  addRandomPositionOffset: vi.fn((pos: any) => pos),
}));

describe('Node Factory', () => {
  describe('createNodeFromBlock', () => {
    const mockBlockDefinition: BlockDefinition = {
      name: 'Test Block',
      key: 'TEST_BLOCK',
      type: 'TestBlock',
      children: null,
      parameters: {
        value: { type: 'float', default: 1.0, desc: null, overload: null }
      },
      init_parameters: {
        mode: { type: 'string', default: 'test', desc: null, overload: null }
      },
      inputs: [{ name: 'in', id: 'in', type: 'float', desc: null, multiple: false }],
      outputs: [{ name: 'out', id: 'out', type: 'float', desc: null }],
      pip_dependencies: [{ name: 'numpy', v: null }],
    };

    it('should create a standard block node', () => {
      const options: CreateNodeOptions = {
        blockDefinition: mockBlockDefinition,
        position: { x: 100, y: 200 },
      };

      const node = createNodeFromBlock(options);

      expect(node.type).toBe('TestBlock');
      expect(node.position).toEqual({ x: 100, y: 200 });
      expect(node.data.func).toBe('TEST_BLOCK');
      expect(node.data.isCustom).toBeUndefined();
      expect(node.data.path).toBe('');
    });

    it('should create a custom block node with path', () => {
      const options: CreateNodeOptions = {
        blockDefinition: mockBlockDefinition,
        position: { x: 100, y: 200 },
        label: 'My Custom Block',
        isCustom: true,
        customPath: 'atlasvibe_blocks/MY_CUSTOM_BLOCK',
      };

      const node = createNodeFromBlock(options);

      expect(node.data.label).toBe('My Custom Block');
      expect(node.data.isCustom).toBe(true);
      expect(node.data.path).toBe('atlasvibe_blocks/MY_CUSTOM_BLOCK');
    });

    it('should throw error for custom block without path', () => {
      const options: CreateNodeOptions = {
        blockDefinition: mockBlockDefinition,
        position: { x: 100, y: 200 },
        isCustom: true,
        // Missing customPath
      };

      expect(() => createNodeFromBlock(options)).toThrow('Custom blocks must have a path');
    });

    it('should handle CONSTANT block with default value', () => {
      const constantBlock: BlockDefinition = {
        name: 'Constant',
        key: 'CONSTANT',
        type: 'Constant',
        children: null,
        parameters: {
          constant: { type: 'float', default: 42.0, desc: null, overload: null }
        },
        inputs: [],
        outputs: [{ name: 'output', id: 'output', type: 'float', desc: null }],
      };

      const options: CreateNodeOptions = {
        blockDefinition: constantBlock,
        position: { x: 0, y: 0 },
      };

      const node = createNodeFromBlock(options);

      expect(node.data.func).toBe('CONSTANT');
      expect(node.data.label).toBe('42');
    });
  });

  describe('duplicateNode', () => {
    const mockNode: Node<BlockData> = {
      id: 'original-1',
      type: 'TestBlock',
      position: { x: 100, y: 100 },
      data: {
        id: 'original-1',
        label: 'Test Block 1',
        func: 'TEST_BLOCK',
        type: 'TestBlock',
        ctrls: { value: { type: 'float', default: 5.0, desc: null, overload: null, functionName: 'TEST_BLOCK', param: 'value', value: 5.0 } },
        inputs: [],
        outputs: [],
        path: ''
      },
      selected: false,
    };

    it('should duplicate a standard node', () => {
      const takenLabels = [{ 0: 'Test Block 1' }] as RegExpMatchArray[];
      const newNode = duplicateNode(mockNode, takenLabels);

      expect(newNode.id).not.toBe(mockNode.id);
      expect(newNode.data.id).not.toBe(mockNode.data.id);
      expect(newNode.data.label).toBe('TEST_BLOCK 2');
      expect(newNode.position).toEqual({ x: 130, y: 130 });
      expect(newNode.selected).toBe(true);
    });

    it('should duplicate a custom node preserving path', () => {
      const customNode: Node<BlockData> = {
        ...mockNode,
        data: {
          ...mockNode.data,
          isCustom: true,
          path: 'atlasvibe_blocks/MY_CUSTOM',
        },
      };

      const newNode = duplicateNode(customNode, []);

      expect(newNode.data.isCustom).toBe(true);
      expect(newNode.data.path).toBe('atlasvibe_blocks/MY_CUSTOM');
    });

    it('should handle CONSTANT node duplication', () => {
      const constantNode: Node<BlockData> = {
        ...mockNode,
        data: {
          ...mockNode.data,
          func: 'CONSTANT',
          ctrls: {
            constant: { type: 'float', default: 99, desc: null, overload: null, functionName: 'CONSTANT', param: 'constant', value: 99 }
          },
        },
      };

      const newNode = duplicateNode(constantNode, []);

      expect(newNode.data.label).toBe('99');
    });
  });
});

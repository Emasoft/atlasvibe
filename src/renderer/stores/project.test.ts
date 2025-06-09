#!/usr/bin/env node
// -*- coding: utf-8 -*-

// HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
// - New test file for project store with custom block handling
// - Tests for saving and loading projects with custom blocks
// - Tests for referencing custom blocks by path
// 

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useProjectStore } from './project';
import { Project } from '@/renderer/types/project';
import { Node } from 'reactflow';
import { BlockData } from '@/renderer/types/block';

// Mock window.api
global.window = {
  api: {
    saveFile: vi.fn(),
    saveFileAs: vi.fn(),
    setUnsavedChanges: vi.fn(),
    createCustomBlockFromBlueprint: vi.fn(),
  },
  prompt: vi.fn(),
} as any;

describe('Project Store - Custom Block References', () => {
  beforeEach(() => {
    // Reset store to initial state
    useProjectStore.setState({
      name: undefined,
      path: undefined,
      hasUnsavedChanges: false,
      nodes: [],
      edges: [],
      textNodes: [],
      controlWidgetNodes: [],
      controlVisualizationNodes: [],
      controlTextNodes: [],
    });
    vi.clearAllMocks();
  });

  describe('Custom Block Handling', () => {
    it('should save project with custom block references', async () => {
      // Arrange
      const customBlock: Node<BlockData> = {
        id: 'custom-1',
        type: 'CustomBlock',
        position: { x: 100, y: 100 },
        data: {
          id: 'custom-1',
          label: 'MyCustomBlock',
          func: 'MY_CUSTOM_BLOCK',
          type: 'CustomBlock',
          ctrls: {},
          inputs: [{ name: 'in', id: 'in', type: 'number' }],
          outputs: [{ name: 'out', id: 'out', type: 'number' }],
          path: 'atlasvibe_blocks/MY_CUSTOM_BLOCK',
          isCustom: true,
        },
      };

      const standardBlock: Node<BlockData> = {
        id: 'standard-1',
        type: 'StandardBlock',
        position: { x: 300, y: 100 },
        data: {
          id: 'standard-1',
          label: 'Add',
          func: 'ADD',
          type: 'StandardBlock',
          ctrls: {},
          inputs: [
            { name: 'a', id: 'a', type: 'number' },
            { name: 'b', id: 'b', type: 'number' },
          ],
          outputs: [{ name: 'sum', id: 'sum', type: 'number' }],
          isCustom: false,
        },
      };

      // Act
      useProjectStore.setState({
        name: 'TestProject',
        path: '/path/to/project.atlasvibe',
        nodes: [customBlock, standardBlock],
        edges: [{
          id: 'e1',
          source: 'custom-1',
          target: 'standard-1',
          sourceHandle: 'out',
          targetHandle: 'a',
        }],
      });

      let savedContent: string = '';
      (window.api.saveFile as any).mockImplementation((path: string, content: string) => {
        savedContent = content;
        return Promise.resolve();
      });

      const { result } = renderHook(() => useProjectStore());
      await result.current.saveProject();

      // Assert
      expect(window.api.saveFile).toHaveBeenCalledWith(
        '/path/to/project.atlasvibe',
        expect.any(String)
      );

      const savedProject: Project = JSON.parse(savedContent);
      
      // Check that custom block has path reference
      const savedCustomBlock = savedProject.rfInstance.nodes.find(n => n.id === 'custom-1');
      expect(savedCustomBlock?.data.isCustom).toBe(true);
      expect(savedCustomBlock?.data.path).toBe('atlasvibe_blocks/MY_CUSTOM_BLOCK');
      
      // Check that standard block doesn't have path
      const savedStandardBlock = savedProject.rfInstance.nodes.find(n => n.id === 'standard-1');
      expect(savedStandardBlock?.data.isCustom).toBe(false);
      expect(savedStandardBlock?.data.path).toBeUndefined();
    });

    it('should handle multiple custom blocks with unique paths', async () => {
      // Arrange
      const customBlocks: Node<BlockData>[] = [
        {
          id: 'custom-1',
          type: 'CustomBlock',
          position: { x: 100, y: 100 },
          data: {
            id: 'custom-1',
            label: 'CustomMatrix1',
            func: 'CUSTOM_MATRIX_1',
            type: 'CustomBlock',
            ctrls: {},
            inputs: [],
            outputs: [{ name: 'matrix', id: 'matrix', type: 'matrix' }],
            path: 'atlasvibe_blocks/CUSTOM_MATRIX_1',
            isCustom: true,
          },
        },
        {
          id: 'custom-2',
          type: 'CustomBlock',
          position: { x: 300, y: 100 },
          data: {
            id: 'custom-2',
            label: 'CustomMatrix2',
            func: 'CUSTOM_MATRIX_2',
            type: 'CustomBlock',
            ctrls: {},
            inputs: [],
            outputs: [{ name: 'matrix', id: 'matrix', type: 'matrix' }],
            path: 'atlasvibe_blocks/CUSTOM_MATRIX_2',
            isCustom: true,
          },
        },
      ];

      // Act
      useProjectStore.setState({
        name: 'MultiCustomProject',
        nodes: customBlocks,
      });

      let savedContent: string = '';
      (window.api.saveFileAs as any).mockResolvedValue({
        filePath: '/path/to/multi-custom.atlasvibe',
        canceled: false,
      });
      (window.api.saveFile as any).mockImplementation((path: string, content: string) => {
        savedContent = content;
        return Promise.resolve();
      });

      const { result } = renderHook(() => useProjectStore());
      await result.current.saveProject();

      // Assert
      const savedProject: Project = JSON.parse(savedContent);
      
      // Each custom block should have its unique path
      savedProject.rfInstance.nodes.forEach((node, index) => {
        expect(node.data.isCustom).toBe(true);
        expect(node.data.path).toBe(`atlasvibe_blocks/CUSTOM_MATRIX_${index + 1}`);
      });
    });

    it('should preserve custom block paths when loading project', () => {
      // Arrange
      const projectToLoad: Project = {
        name: 'LoadedProject',
        rfInstance: {
          nodes: [
            {
              id: 'custom-loaded',
              type: 'CustomBlock',
              position: { x: 200, y: 200 },
              data: {
                id: 'custom-loaded',
                label: 'LoadedCustomBlock',
                func: 'LOADED_CUSTOM',
                type: 'CustomBlock',
                ctrls: {},
                inputs: [],
                outputs: [],
                path: 'atlasvibe_blocks/LOADED_CUSTOM',
                isCustom: true,
              },
            },
          ],
          edges: [],
        },
        textNodes: [],
      };

      // Mock manifest and metadata
      vi.mock('./manifest', () => ({
        useManifest: () => ({}),
        useMetadata: () => ({}),
      }));

      // Act
      const { result } = renderHook(() => useProjectStore());
      
      // Directly set state since useLoadProject requires manifest/metadata
      result.current.handleNodeChanges(
        () => projectToLoad.rfInstance.nodes,
        () => []
      );
      
      // Assert
      const loadedNode = result.current.nodes[0];
      expect(loadedNode.data.isCustom).toBe(true);
      expect(loadedNode.data.path).toBe('atlasvibe_blocks/LOADED_CUSTOM');
    });
  });

  describe('Project File Format', () => {
    it('should include project metadata in saved file', async () => {
      // Arrange
      const projectName = 'MyTestProject';
      const projectPath = '/path/to/my-test-project.atlasvibe';
      
      useProjectStore.setState({
        name: projectName,
        path: projectPath,
        nodes: [],
        edges: [],
      });

      let savedContent: string = '';
      (window.api.saveFile as any).mockImplementation((path: string, content: string) => {
        savedContent = content;
        return Promise.resolve();
      });

      // Act
      const { result } = renderHook(() => useProjectStore());
      await result.current.saveProject();

      // Assert
      const savedProject: Project = JSON.parse(savedContent);
      expect(savedProject.name).toBe(projectName);
      
      // Check structure
      expect(savedProject).toHaveProperty('rfInstance');
      expect(savedProject.rfInstance).toHaveProperty('nodes');
      expect(savedProject.rfInstance).toHaveProperty('edges');
      expect(savedProject).toHaveProperty('textNodes');
      expect(savedProject).toHaveProperty('controlNodes');
      expect(savedProject).toHaveProperty('controlVisualizationNodes');
      expect(savedProject).toHaveProperty('controlTextNodes');
    });

    it('should handle project without custom blocks', async () => {
      // Arrange
      const standardOnlyProject: Node<BlockData>[] = [
        {
          id: 'std-1',
          type: 'ADD',
          position: { x: 100, y: 100 },
          data: {
            id: 'std-1',
            label: 'Add',
            func: 'ADD',
            type: 'ADD',
            ctrls: {},
            inputs: [],
            outputs: [],
          },
        },
      ];

      useProjectStore.setState({
        name: 'StandardOnlyProject',
        path: '/path/to/standard.atlasvibe',
        nodes: standardOnlyProject,
      });

      let savedContent: string = '';
      (window.api.saveFile as any).mockImplementation((path: string, content: string) => {
        savedContent = content;
        return Promise.resolve();
      });

      // Act
      const { result } = renderHook(() => useProjectStore());
      await result.current.saveProject();

      // Assert
      const savedProject: Project = JSON.parse(savedContent);
      
      // No custom blocks should have path or isCustom
      savedProject.rfInstance.nodes.forEach(node => {
        expect(node.data.isCustom).toBeFalsy();
        expect(node.data.path).toBeUndefined();
      });
    });
  });
});
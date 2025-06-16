#!/usr/bin/env node
// -*- coding: utf-8 -*-

// HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
// - New hook for Save As functionality with custom dialog
// - Integrates SaveProjectDialog component
// - Handles project creation and validation
// 

import { useState } from "react";
import { toast } from "sonner";
import useWithPermission from "./useWithPermission";
import { useProjectStore } from "@/renderer/stores/project";
import { useShallow } from "zustand/react/shallow";
import { SaveProjectDialog } from "@/renderer/components/SaveProjectDialog";
import { fromPromise } from "neverthrow";

export const useSaveAs = () => {
  const { withPermissionCheck } = useWithPermission();
  const [dialogOpen, setDialogOpen] = useState(false);
  
  const { name, setProjectName } = useProjectStore(
    useShallow((state) => ({
      name: state.name,
      setProjectName: state.setProjectName,
    }))
  );

  const handleSaveAs = () => {
    setDialogOpen(true);
  };

  const handleSave = async (projectPath: string, projectName: string) => {
    // Update project name in store
    setProjectName(projectName);
    
    // Create project directory
    const createResult = await fromPromise(
      window.api.createDirectory(projectPath),
      (e) => e as Error
    );

    if (createResult.isErr()) {
      throw new Error(`Failed to create project directory: ${createResult.error.message}`);
    }

    // Save project file
    const project = useProjectStore.getState();
    const projectData = {
      version: '2.0.0',
      name: projectName,
      rfInstance: {
        nodes: project.nodes,
        edges: project.edges,
      },
      textNodes: project.textNodes,
      controlNodes: project.controlWidgetNodes,
      controlVisualizationNodes: project.controlVisualizationNodes,
      controlTextNodes: project.controlTextNodes,
    };

    const fileContent = JSON.stringify(projectData, undefined, 4);
    const filePath = `${projectPath}/${projectName}.atlasvibe`;

    const saveResult = await fromPromise(
      window.api.saveFile(filePath, fileContent),
      (e) => e as Error
    );

    if (saveResult.isErr()) {
      throw new Error(`Failed to save project file: ${saveResult.error.message}`);
    }

    // Update project path in store
    useProjectStore.setState({ 
      path: filePath,
      hasUnsavedChanges: false,
    });

    // Update window title
    window.api.setUnsavedChanges(false);
  };

  const SaveAsComponent = () => (
    <SaveProjectDialog
      open={dialogOpen}
      onOpenChange={setDialogOpen}
      onSave={handleSave}
      defaultName={name || "Untitled_Project"}
    />
  );

  return {
    handleSaveAs: withPermissionCheck(handleSaveAs),
    SaveAsDialog: SaveAsComponent,
  };
};
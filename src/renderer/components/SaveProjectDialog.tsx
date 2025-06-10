#!/usr/bin/env node
// -*- coding: utf-8 -*-

// HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
// - New component for custom project save dialog
// - Allows saving to any folder with folder browser
// - Validates project names with same rules as blocks
// - Implements space replacement with two-step confirmation
// - Detects name collisions
// 

import { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/renderer/components/ui/dialog";
import { Button } from "@/renderer/components/ui/button";
import { Input } from "@/renderer/components/ui/input";
import { Label } from "@/renderer/components/ui/label";
import { cn } from "@/renderer/lib/utils";
import { FolderOpen } from "lucide-react";
import { toast } from "sonner";

interface SaveProjectDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSave: (projectPath: string, projectName: string) => Promise<void>;
  defaultName?: string;
}

// Valid project name pattern (same as block names)
const VALID_NAME_PATTERN = /^[A-Za-z][A-Za-z_]*$/;

export function SaveProjectDialog({
  open,
  onOpenChange,
  onSave,
  defaultName = "",
}: SaveProjectDialogProps) {
  const [projectName, setProjectName] = useState(defaultName);
  const [folderPath, setFolderPath] = useState("");
  const [nameError, setNameError] = useState("");
  const [isValidating, setIsValidating] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [showPreview, setShowPreview] = useState(false);
  const [previewName, setPreviewName] = useState("");
  const [nameCollision, setNameCollision] = useState(false);

  // Reset state when dialog opens/closes
  useEffect(() => {
    if (open) {
      setProjectName(defaultName);
      setFolderPath("");
      setNameError("");
      setShowPreview(false);
      setPreviewName("");
      setNameCollision(false);
    }
  }, [open, defaultName]);

  // Validate project name
  const validateName = (name: string): string => {
    if (!name || name.trim().length === 0) {
      return "Name cannot be empty";
    }

    if (!VALID_NAME_PATTERN.test(name)) {
      if (/^\d/.test(name)) {
        return "Name must start with a letter";
      }
      return "Name can only contain letters (A-Z, a-z) and underscores (_)";
    }

    return "";
  };

  // Clean name by replacing spaces with underscores
  const cleanName = (name: string): string => {
    // Trim leading/trailing spaces
    let cleaned = name.trim();
    
    // Replace multiple spaces with single underscore
    cleaned = cleaned.replace(/\s+/g, "_");
    
    // Remove any non-alphanumeric characters except underscore
    cleaned = cleaned.replace(/[^A-Za-z0-9_]/g, "");
    
    // Ensure it starts with a letter
    if (/^\d/.test(cleaned)) {
      cleaned = "Project_" + cleaned;
    }
    
    return cleaned || "Untitled_Project";
  };

  // Handle name input change
  const handleNameChange = (value: string) => {
    setProjectName(value);
    setShowPreview(false);
    setPreviewName("");
    
    const error = validateName(value);
    setNameError(error);
  };

  // Handle folder selection
  const handleBrowseFolder = async () => {
    const result = await window.api.selectFolder();
    if (!result.canceled && result.filePaths[0]) {
      setFolderPath(result.filePaths[0]);
      
      // Check for name collision
      if (projectName) {
        checkNameCollision(result.filePaths[0], projectName);
      }
    }
  };

  // Check if project already exists
  const checkNameCollision = async (folder: string, name: string) => {
    const projectPath = `${folder}/${name}`;
    const exists = await window.api.pathExists(projectPath);
    setNameCollision(exists);
  };

  // Handle save button click
  const handleSave = async () => {
    // First click: show preview if name needs cleaning
    if (!showPreview && projectName !== cleanName(projectName)) {
      const cleaned = cleanName(projectName);
      setPreviewName(cleaned);
      setShowPreview(true);
      setProjectName(cleaned);
      
      // Validate cleaned name
      const error = validateName(cleaned);
      setNameError(error);
      
      // Check collision with cleaned name
      if (folderPath && !error) {
        checkNameCollision(folderPath, cleaned);
      }
      return;
    }

    // Validate inputs
    const error = validateName(projectName);
    if (error) {
      setNameError(error);
      return;
    }

    if (!folderPath) {
      toast.error("Please select a folder");
      return;
    }

    // Handle name collision
    if (nameCollision) {
      const confirmed = await window.api.showConfirmDialog({
        title: "Project Already Exists",
        message: `A project with the name "${projectName}" already exists in the selected folder. Do you want to overwrite it?`,
        buttons: ["Overwrite", "Cancel"],
        defaultId: 1,
        cancelId: 1,
      });

      if (confirmed.response === 1) {
        return; // User clicked Cancel
      }
    }

    // Save project
    setIsSaving(true);
    try {
      const projectPath = `${folderPath}/${projectName}`;
      await onSave(projectPath, projectName);
      onOpenChange(false);
      toast.success(`Project saved to ${projectPath}`);
    } catch (error) {
      console.error("Save error:", error);
      toast.error(`Failed to save project: ${error.message}`);
    } finally {
      setIsSaving(false);
    }
  };

  const isValid = !nameError && projectName && folderPath;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Save Project</DialogTitle>
          <DialogDescription>
            Choose a location and name for your project
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 py-4">
          {/* Folder selection */}
          <div className="grid gap-2">
            <Label htmlFor="folder">Project Location</Label>
            <div className="flex gap-2">
              <Input
                id="folder"
                placeholder="Select folder"
                value={folderPath}
                readOnly
                className="flex-1"
              />
              <Button
                type="button"
                variant="outline"
                size="icon"
                onClick={handleBrowseFolder}
              >
                <FolderOpen className="h-4 w-4" />
              </Button>
            </div>
          </div>

          {/* Project name */}
          <div className="grid gap-2">
            <Label htmlFor="name">Project Name</Label>
            <Input
              id="name"
              placeholder="Project name"
              value={projectName}
              onChange={(e) => handleNameChange(e.target.value)}
              className={cn(nameError && "border-red-500")}
            />
            
            {/* Error message */}
            {nameError && (
              <p className="error-message text-sm text-red-500">{nameError}</p>
            )}
            
            {/* Preview message */}
            {showPreview && (
              <p className="preview-message text-sm text-yellow-600">
                Project will be saved as: {projectName}
              </p>
            )}
            
            {/* Collision warning */}
            {nameCollision && !nameError && (
              <p className="warning-message text-sm text-yellow-600">
                A project with this name already exists in the selected folder. Do you want to overwrite it?
              </p>
            )}
          </div>
        </div>

        <DialogFooter className="gap-2">
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isSaving}
          >
            Cancel
          </Button>
          
          {nameCollision && !nameError && (
            <Button
              variant="destructive"
              onClick={handleSave}
              disabled={!isValid || isSaving}
            >
              {isSaving ? "Saving..." : "Overwrite"}
            </Button>
          )}
          
          {!nameCollision && (
            <Button
              onClick={handleSave}
              disabled={!isValid || isSaving}
            >
              {isSaving ? "Saving..." : "Save"}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
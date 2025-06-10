#!/usr/bin/env tsx
// -*- coding: utf-8 -*-

// HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
// - New component for saving blocks as blueprints
// - Validates blueprint names with same rules as blocks
// - Detects name collisions
// - Implements two-step space replacement
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
import { toast } from "sonner";
import { saveBlueprintFromBlock } from "@/renderer/lib/api";

interface SaveBlueprintDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  blockId: string;
  blockPath?: string;
  defaultName?: string;
  existingBlueprints?: string[];
}

// Valid blueprint name pattern (same as block names)
const VALID_NAME_PATTERN = /^[A-Za-z][A-Za-z_]*$/;

export function SaveBlueprintDialog({
  open,
  onOpenChange,
  blockId,
  blockPath,
  defaultName = "",
  existingBlueprints = [],
}: SaveBlueprintDialogProps) {
  const [blueprintName, setBlueprintName] = useState(defaultName);
  const [nameError, setNameError] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [showPreview, setShowPreview] = useState(false);
  const [previewName, setPreviewName] = useState("");
  const [nameCollision, setNameCollision] = useState(false);

  // Reset state when dialog opens/closes
  useEffect(() => {
    if (open) {
      setBlueprintName(defaultName);
      setNameError("");
      setShowPreview(false);
      setPreviewName("");
      setNameCollision(false);
    }
  }, [open, defaultName]);

  // Validate blueprint name
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
      cleaned = "Blueprint_" + cleaned;
    }
    
    return cleaned || "Custom_Blueprint";
  };

  // Handle name input change
  const handleNameChange = (value: string) => {
    setBlueprintName(value);
    setShowPreview(false);
    setPreviewName("");
    
    const error = validateName(value);
    setNameError(error);
    
    // Check for collision
    if (!error && existingBlueprints.includes(value)) {
      setNameCollision(true);
    } else {
      setNameCollision(false);
    }
  };

  // Handle save button click
  const handleSave = async () => {
    // First click: show preview if name needs cleaning
    if (!showPreview && blueprintName !== cleanName(blueprintName)) {
      const cleaned = cleanName(blueprintName);
      setPreviewName(cleaned);
      setShowPreview(true);
      setBlueprintName(cleaned);
      
      // Validate cleaned name
      const error = validateName(cleaned);
      setNameError(error);
      
      // Check collision with cleaned name
      if (!error && existingBlueprints.includes(cleaned)) {
        setNameCollision(true);
      }
      return;
    }

    // Validate inputs
    const error = validateName(blueprintName);
    if (error) {
      setNameError(error);
      return;
    }

    // Handle name collision
    if (nameCollision) {
      const confirmed = window.confirm(
        `A blueprint with the name "${blueprintName}" already exists. Do you want to overwrite it?`
      );

      if (!confirmed) {
        return;
      }
    }

    // Save blueprint
    setIsSaving(true);
    try {
      if (!blockPath) {
        throw new Error("Block path is required to save as blueprint");
      }

      const result = await saveBlueprintFromBlock({
        blockPath,
        blueprintName,
        overwrite: nameCollision,
      });

      if (result.isErr()) {
        throw new Error(result.error.message);
      }

      onOpenChange(false);
      toast.success(`Blueprint "${blueprintName}" saved successfully`);
    } catch (error: any) {
      console.error("Save blueprint error:", error);
      toast.error(`Failed to save blueprint: ${error.message}`);
    } finally {
      setIsSaving(false);
    }
  };

  const isValid = !nameError && blueprintName;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Save as Blueprint</DialogTitle>
          <DialogDescription>
            Save this custom block as a reusable blueprint in the global palette
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 py-4">
          <div className="grid gap-2">
            <Label htmlFor="name">Blueprint Name</Label>
            <Input
              id="name"
              placeholder="Enter blueprint name"
              value={blueprintName}
              onChange={(e) => handleNameChange(e.target.value)}
              className={cn(nameError && "border-red-500")}
              autoFocus
            />
            
            {/* Error message */}
            {nameError && (
              <p className="error-message text-sm text-red-500">{nameError}</p>
            )}
            
            {/* Preview message */}
            {showPreview && (
              <p className="preview-message text-sm text-yellow-600">
                Name will be saved as: {blueprintName}
              </p>
            )}
            
            {/* Collision warning */}
            {nameCollision && !nameError && (
              <p className="warning-message text-sm text-yellow-600">
                A blueprint with this name already exists. Do you want to overwrite it?
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
/*
 * Copyright (c) 2024 Emasoft
 *
 * This file is part of AtlasVibe, which is based on Flojoy Studio
 * Original Copyright (c) 2023-2024 Flojoy
 *
 * SPDX-License-Identifier: MIT
 * See the LICENSE file for details.
 */

#!/usr/bin/env tsx
// -*- coding: utf-8 -*-

// HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
// - New component for managing blueprints
// - Lists all blueprints with rename and delete options
// - Validates names with two-step space replacement
// - Handles name collision detection
//

import { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/renderer/components/ui/dialog";
import { Button } from "@/renderer/components/ui/button";
import { Input } from "@/renderer/components/ui/input";
import { cn } from "@/renderer/lib/utils";
import { Edit2, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { useManifest } from "@/renderer/stores/manifest";
import { renameBlueprint, deleteBlueprint } from "@/renderer/lib/api";
import { TreeNode, BlockDefinition } from "@/renderer/types/manifest";

interface BlueprintManagerDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

interface BlueprintItem {
  key: string;
  name: string;
  category?: string;
}

// Valid blueprint name pattern
const VALID_NAME_PATTERN = /^[A-Za-z][A-Za-z_]*$/;

export function BlueprintManagerDialog({
  open,
  onOpenChange,
}: BlueprintManagerDialogProps) {
  const [blueprints, setBlueprints] = useState<BlueprintItem[]>([]);
  const [editingKey, setEditingKey] = useState<string | null>(null);
  const [editingName, setEditingName] = useState("");
  const [nameError, setNameError] = useState("");
  const [showPreview, setShowPreview] = useState(false);

  const manifest = useManifest();

  // Helper function to extract blueprints from manifest tree
  const extractBlueprints = (node: TreeNode, category: string = ""): BlueprintItem[] => {
    const items: BlueprintItem[] = [];

    if ('children' in node && node.children) {
      // This is a section node
      node.children.forEach((child) => {
        const childCategory = category ? `${category}/${child.name}` : child.name;
        items.push(...extractBlueprints(child, childCategory));
      });
    } else if ('key' in node && node.key && (node as BlockDefinition).isBlueprint) {
      // This is a leaf node (block definition)
      items.push({
        key: node.key,
        name: node.name,
        category: category,
      });
    }

    return items;
  };

  // Load blueprints from manifest
  useEffect(() => {
    if (manifest && open) {
      const blueprintList = extractBlueprints(manifest);
      setBlueprints(blueprintList.sort((a, b) => a.name.localeCompare(b.name)));
    }
  }, [manifest, open]);

  // Validate name
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

    // Check for collision with other blueprints
    const otherBlueprints = blueprints.filter(b => b.key !== editingKey);
    if (otherBlueprints.some(b => b.name === name)) {
      return "A blueprint with this name already exists";
    }

    return "";
  };

  // Clean name
  const cleanName = (name: string): string => {
    let cleaned = name.trim();
    cleaned = cleaned.replace(/\s+/g, "_");
    cleaned = cleaned.replace(/[^A-Za-z0-9_]/g, "");

    if (/^\d/.test(cleaned)) {
      cleaned = "Blueprint_" + cleaned;
    }

    return cleaned || "Renamed_Blueprint";
  };

  // Start editing
  const startEdit = (blueprint: BlueprintItem) => {
    setEditingKey(blueprint.key);
    setEditingName(blueprint.name);
    setNameError("");
    setShowPreview(false);
  };

  // Cancel editing
  const cancelEdit = () => {
    setEditingKey(null);
    setEditingName("");
    setNameError("");
    setShowPreview(false);
  };

  // Handle name change
  const handleNameChange = (value: string) => {
    setEditingName(value);
    setShowPreview(false);

    const error = validateName(value);
    setNameError(error);
  };

  // Save rename
  const saveRename = async () => {
    if (!editingKey) return;

    // First click: show preview if name needs cleaning
    if (!showPreview && editingName !== cleanName(editingName)) {
      const cleaned = cleanName(editingName);
      setEditingName(cleaned);
      setShowPreview(true);

      const error = validateName(cleaned);
      setNameError(error);
      return;
    }

    // Validate
    const error = validateName(editingName);
    if (error) {
      setNameError(error);
      return;
    }

    try {
      const result = await renameBlueprint({
        oldName: editingKey,
        newName: editingName,
      });

      if (result.isErr()) {
        throw new Error(result.error.message);
      }

      toast.success(`Blueprint renamed to "${editingName}"`);
      cancelEdit();

      // Reload blueprints
      if (manifest) {
        // Trigger manifest reload
        window.location.reload();
      }
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      toast.error(`Failed to rename blueprint: ${errorMessage}`);
    }
  };

  // Delete blueprint
  const handleDelete = async (blueprint: BlueprintItem) => {
    const confirmed = window.confirm(
      `Are you sure you want to delete the blueprint "${blueprint.name}"? This cannot be undone.`
    );

    if (!confirmed) return;

    try {
      const result = await deleteBlueprint({ blueprintName: blueprint.key });

      if (result.isErr()) {
        throw new Error(result.error.message);
      }

      toast.success(`Blueprint "${blueprint.name}" deleted`);

      // Reload blueprints
      window.location.reload();
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      toast.error(`Failed to delete blueprint: ${errorMessage}`);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>Blueprint Manager</DialogTitle>
          <DialogDescription>
            Manage your saved blueprints. Rename or delete blueprints as needed.
          </DialogDescription>
        </DialogHeader>

        <div className="max-h-[400px] overflow-y-auto">
          {blueprints.length === 0 ? (
            <p className="py-8 text-center text-muted-foreground">
              No blueprints found. Create blueprints by saving custom blocks.
            </p>
          ) : (
            <div className="space-y-2">
              {blueprints.map((blueprint) => (
                <div
                  key={blueprint.key}
                  className="blueprint-item flex items-center gap-2 rounded-lg border p-3"
                  data-testid="blueprint-item"
                >
                  {editingKey === blueprint.key ? (
                    <>
                      <Input
                        value={editingName}
                        onChange={(e) => handleNameChange(e.target.value)}
                        className={cn(
                          "flex-1",
                          nameError && "border-red-500"
                        )}
                        placeholder="Enter new name"
                        autoFocus
                        onKeyPress={(e) => {
                          if (e.key === "Enter") saveRename();
                          if (e.key === "Escape") cancelEdit();
                        }}
                      />
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={saveRename}
                        disabled={!!nameError && !showPreview}
                        className="rename-button"
                        data-testid="rename-button"
                      >
                        {showPreview ? "Apply" : "Rename"}
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={cancelEdit}
                      >
                        Cancel
                      </Button>
                    </>
                  ) : (
                    <>
                      <div className="flex-1">
                        <span className="font-medium">{blueprint.name}</span>
                        {blueprint.category && (
                          <span className="ml-2 text-sm text-muted-foreground">
                            ({blueprint.category})
                          </span>
                        )}
                      </div>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => startEdit(blueprint)}
                        className="rename-button"
                      >
                        <Edit2 className="h-4 w-4" />
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleDelete(blueprint)}
                        className="text-red-600 hover:text-red-700"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Error/preview messages */}
          {editingKey && nameError && (
            <p className="error-message mt-2 text-sm text-red-500">{nameError}</p>
          )}
          {editingKey && showPreview && (
            <p className="preview-message mt-2 text-sm text-yellow-600">
              Name will be changed to: {editingName}
            </p>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

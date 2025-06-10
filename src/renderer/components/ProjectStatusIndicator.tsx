#!/usr/bin/env node
// -*- coding: utf-8 -*-

// HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
// - New component for project save status indicator
// - Shows status: saved, unsaved changes, saving, autosaving
// - Implements color scheme readable on black background
// - Includes transaction queue for autosave
// 

import { useEffect, useState, useRef } from "react";
import { cn } from "@/renderer/lib/utils";
import { useProjectStore } from "@/renderer/stores/project";
import { useShallow } from "zustand/react/shallow";

export type ProjectStatus = "saved" | "unsaved" | "saving" | "autosaving";

interface Transaction {
  id: string;
  timestamp: number;
  action: () => Promise<void>;
}

export const ProjectStatusIndicator = () => {
  const { name, path, hasUnsavedChanges, isSaving, saveProject } = useProjectStore(
    useShallow((state) => ({
      name: state.name,
      path: state.path,
      hasUnsavedChanges: state.hasUnsavedChanges,
      isSaving: state.isSaving,
      saveProject: state.saveProject,
    }))
  );

  const [status, setStatus] = useState<ProjectStatus>("saved");
  const [transactionQueue, setTransactionQueue] = useState<Transaction[]>([]);
  const autosaveTimerRef = useRef<NodeJS.Timeout | null>(null);
  const isProcessingRef = useRef(false);

  // Transaction queue processor
  useEffect(() => {
    const processQueue = async () => {
      if (isProcessingRef.current || transactionQueue.length === 0) {
        return;
      }

      isProcessingRef.current = true;
      setStatus("autosaving");

      // Process all transactions in queue
      const transactions = [...transactionQueue];
      setTransactionQueue([]);

      try {
        for (const transaction of transactions) {
          await transaction.action();
        }
        
        // Log transactions for recovery
        if (path) {
          const transactionLog = {
            timestamp: Date.now(),
            transactionCount: transactions.length,
            projectPath: path,
          };
          window.api.logTransaction?.(JSON.stringify(transactionLog));
        }

        setStatus("saved");
      } catch (error) {
        console.error("Autosave error:", error);
        // Re-queue failed transactions
        setTransactionQueue(transactions);
        setStatus("unsaved");
      } finally {
        isProcessingRef.current = false;
      }
    };

    processQueue();
  }, [transactionQueue, path]);

  // Update status based on isSaving from store
  useEffect(() => {
    if (isSaving) {
      setStatus("saving");
    }
  }, [isSaving]);

  // Update status based on unsaved changes
  useEffect(() => {
    if (hasUnsavedChanges && !isSaving && status !== "autosaving") {
      setStatus("unsaved");
      
      // Clear existing autosave timer
      if (autosaveTimerRef.current) {
        clearTimeout(autosaveTimerRef.current);
      }

      // Set new autosave timer (2 seconds of inactivity)
      autosaveTimerRef.current = setTimeout(() => {
        if (path) {
          // Add save action to transaction queue
          const transaction: Transaction = {
            id: `autosave-${Date.now()}`,
            timestamp: Date.now(),
            action: async () => {
              await saveProject();
            },
          };
          setTransactionQueue((prev) => [...prev, transaction]);
        }
      }, 2000);
    } else if (!hasUnsavedChanges && !isSaving && status !== "autosaving") {
      setStatus("saved");
    }

    return () => {
      if (autosaveTimerRef.current) {
        clearTimeout(autosaveTimerRef.current);
      }
    };
  }, [hasUnsavedChanges, isSaving, path, saveProject, status]);

  // Status text and color mapping
  const getStatusDisplay = () => {
    const statusMap = {
      saved: {
        text: name ? `Saved - ${name}` : "Saved",
        className: "text-green-400", // rgb(52, 211, 153) - readable green
      },
      unsaved: {
        text: "Unsaved changes",
        className: "text-yellow-400", // rgb(251, 191, 36) - readable yellow
      },
      saving: {
        text: "Saving",
        className: "text-yellow-300", // rgb(252, 211, 77) - lighter yellow
      },
      autosaving: {
        text: "Autosaving",
        className: "text-yellow-200", // rgb(254, 240, 138) - pale yellow
      },
    };

    return statusMap[status];
  };

  const { text, className } = getStatusDisplay();

  return (
    <div
      className={cn(
        "project-status-indicator flex items-center px-3 py-1 text-sm font-medium",
        className
      )}
      data-testid="project-status-indicator"
    >
      {text}
      {status === "autosaving" && (
        <span className="ml-2 inline-block h-2 w-2 animate-pulse rounded-full bg-current" />
      )}
    </div>
  );
};
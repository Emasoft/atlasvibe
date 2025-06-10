#!/usr/bin/env tsx
// -*- coding: utf-8 -*-

// HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
// - New component for showing execution status
// - Shows "Paused - Block Regenerating" when blocks are regenerating
// - Shows "Running" when execution is active
// - Automatically resumes after regeneration
// 

import React, { useEffect, useState } from "react";
import { cn } from "@/renderer/lib/utils";
import { useSocketStore } from "@/renderer/stores/socket";
import { useManifestStore } from "@/renderer/stores/manifest";
import { useShallow } from "zustand/react/shallow";

export type ExecutionStatusType = "idle" | "running" | "paused" | "completed" | "error";

interface ExecutionStatusProps {
  className?: string;
}

export const ExecutionStatus: React.FC<ExecutionStatusProps> = ({ className }) => {
  const [status, setStatus] = useState<ExecutionStatusType>("idle");
  const [pauseReason, setPauseReason] = useState<string>("");
  
  const { isRunning, serverStatus } = useSocketStore(
    useShallow((state) => ({
      isRunning: state.isRunning,
      serverStatus: state.serverStatus,
    }))
  );
  
  const regeneratingBlocks = useManifestStore((state) => state.regeneratingBlocks);
  const hasRegeneratingBlocks = regeneratingBlocks.size > 0;
  
  // Update status based on execution and regeneration state
  useEffect(() => {
    if (hasRegeneratingBlocks && isRunning) {
      setStatus("paused");
      setPauseReason("Block Regenerating");
    } else if (isRunning) {
      setStatus("running");
      setPauseReason("");
    } else {
      setStatus("idle");
      setPauseReason("");
    }
  }, [isRunning, hasRegeneratingBlocks]);
  
  // Auto-resume when regeneration completes
  useEffect(() => {
    if (status === "paused" && !hasRegeneratingBlocks) {
      // Regeneration completed, resume execution
      setStatus("running");
      setPauseReason("");
    }
  }, [status, hasRegeneratingBlocks]);
  
  const getStatusDisplay = () => {
    switch (status) {
      case "running":
        return { text: "Running", className: "text-green-500" };
      case "paused":
        return { 
          text: pauseReason ? `Paused - ${pauseReason}` : "Paused", 
          className: "text-yellow-500" 
        };
      case "completed":
        return { text: "Completed", className: "text-blue-500" };
      case "error":
        return { text: "Error", className: "text-red-500" };
      default:
        return { text: "Idle", className: "text-gray-500" };
    }
  };
  
  const { text, className: statusClassName } = getStatusDisplay();
  
  if (status === "idle") {
    return null; // Don't show status when idle
  }
  
  return (
    <div
      className={cn(
        "execution-status flex items-center gap-2 rounded px-3 py-1 text-sm font-medium",
        statusClassName,
        status === "paused" && "execution-status paused",
        status === "running" && "execution-status running",
        className
      )}
      data-testid="execution-status"
    >
      <span>{text}</span>
      {status === "running" && (
        <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-current" />
      )}
    </div>
  );
};
/*
 * Copyright (c) 2024 Emasoft
 *
 * This file is part of AtlasVibe, which is based on Flojoy Studio
 * Original Copyright (c) 2023-2024 Flojoy
 *
 * SPDX-License-Identifier: MIT
 * See the LICENSE file for details.
 */

import { z } from "zod";
import { BlockResult } from "./block-result";

export enum ServerStatus {
  // all the possible server status that can be received from the server
  STANDBY = "🐢 awaiting a new job",
  RUNNING_PYTHON_JOB = "🏃‍♀️ running python job: ",
  FAILED_BLOCK = "❌ Failed to run: ",
  RUN_PRE_JOB_OP = "⏳ running pre-job operation...",
  BUILDING_TOPOLOGY = " 🔨 building flow chart...",
  MAXIMUM_RUNTIME_EXCEEDED = "⏰ maximum runtime exceeded",
  COLLECTING_PIP_DEPENDENCIES = " 📦 collecting pip dependencies...",
  INSTALLING_PACKAGES = "✨ installing missing packages...",
  IMPORTING_BLOCK_FUNCTIONS = " 📦 importing node functions...",
  PRE_JOB_OP_FAILED = "❌ pre-job operation failed - Re-run script...",
  RUN_IN_PROCESS = "🏃‍♀️ running script...",
  IMPORTING_BLOCK_FUNCTIONS_FAILED = "❌ importing node functions failed",

  // some status we defined only on the client
  OFFLINE = "🛑 server offline",
  CONNECTING = "Connecting to server...",
}

export const ServerStatusEnum = z.nativeEnum(ServerStatus);
export type ServerStatusEnum = z.infer<typeof ServerStatusEnum>;

export const WorkerJobResponse = z.object({
  jobsetId: z.string().optional(),
  socketId: z.string().optional(),
  SYSTEM_STATUS: ServerStatusEnum.optional(),
  type: z.enum([
    "worker_response",
    "connection_established",
    "manifest_update",
    "change_queued",
    "block_code_updated",
    "block_parameter_updated",
    "transaction_applied",
    "transaction_failed",
  ]),
  FAILED_NODES: z.record(z.string()).optional(),
  RUNNING_NODE: z.string().optional(),
  NODE_RESULTS: z
    .object({
      cmd: z.string(),
      id: z.string(),
      result: z.custom<BlockResult>(),
    })
    .optional(),
  blockPaths: z.array(z.string()).optional(), // For manifest_update messages
  // Additional fields for change tracking events
  block_id: z.string().optional(),
  change_type: z.string().optional(),
  has_pending: z.number().optional(),
  version: z.string().optional(),
  parameter: z.string().optional(),
  value: z.unknown().optional(),
  change_count: z.number().optional(),
  error: z.string().optional(),
});

export type WorkerJobResponse = z.infer<typeof WorkerJobResponse>;

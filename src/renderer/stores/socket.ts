/*
 * Copyright (c) 2024 Emasoft
 *
 * This file is part of AtlasVibe, which is based on Flojoy Studio
 * Original Copyright (c) 2023-2024 Flojoy
 *
 * SPDX-License-Identifier: MIT
 * See the LICENSE file for details.
 */

import { create } from "zustand";
import { BlockResult } from "@/renderer/types/block-result";
import {
  ServerStatus,
  ServerStatusEnum,
  WorkerJobResponse,
} from "@/renderer/types/socket";

type State = {
  runningBlock: string;
  blockResults: Record<string, BlockResult>;

  serverStatus: ServerStatusEnum;
  failedBlocks: Record<string, string>;
  socketId: string;
  isRunning: boolean;
};

type Actions = {
  setServerStatus: (val: ServerStatusEnum) => void;
  processWorkerResponse: (res: WorkerJobResponse) => void;
  wipeBlockResults: () => void;
  setSocketId: (val: string) => void;
};

// Don't change this to use Immer,
// it breaks the blockResults setting for some reason??????????
export const useSocketStore = create<State & Actions>()((set) => ({
  serverStatus: ServerStatus.CONNECTING,
  setServerStatus: (val) => {
    set({ serverStatus: val });
  },

  processWorkerResponse: (res) => {
    if (res.SYSTEM_STATUS) {
      const isJobRunning = res.SYSTEM_STATUS === ServerStatus.RUNNING_PYTHON_JOB ||
                          res.SYSTEM_STATUS === ServerStatus.RUN_IN_PROCESS;
      set({
        serverStatus: res.SYSTEM_STATUS,
        isRunning: isJobRunning,
      });
    }
    if (res.NODE_RESULTS) {
      set((state) => {
        const result = res.NODE_RESULTS!;
        return {
          ...state,
          blockResults: {
            ...state.blockResults,
            [result.id]: result.result,
          },
        };
      });
    }
    if (res.RUNNING_NODE) {
      set({ runningBlock: res.RUNNING_NODE, isRunning: true });
    }
    if (res.FAILED_NODES) {
      set({ failedBlocks: res.FAILED_NODES });
    }
  },

  blockResults: {},
  wipeBlockResults: () => {
    set({ blockResults: {} });
  },

  runningBlock: "",
  failedBlocks: {},
  isRunning: false,

  socketId: "",
  setSocketId: (val) => {
    set({ socketId: val });
  },
}));

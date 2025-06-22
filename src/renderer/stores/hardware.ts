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
import { immer } from "zustand/middleware/immer";
import { DeviceInfo } from "@/renderer/types/hardware";
import { getDeviceInfo } from "@/renderer/lib/api";
import { ZodError } from "zod";
import { Result } from "neverthrow";
import { HTTPError } from "ky";

type State = {
  devices: DeviceInfo | undefined;
};

type Actions = {
  refresh: (
    discoverNIDAQmxDevices?: boolean,
    discoverNIDMMDevices?: boolean,
  ) => Promise<Result<void, HTTPError | ZodError>>;
};

export const useHardwareStore = create<State & Actions>()(
  immer((set) => ({
    devices: undefined,
    refresh: async (
      discoverNIDAQmxDevices = false,
      discoverNIDMMDevices = false,
    ) => {
      set({ devices: undefined });
      const res = await getDeviceInfo(
        discoverNIDAQmxDevices,
        discoverNIDMMDevices,
      );
      return res.map((info) => set({ devices: info }));
    },
  })),
);

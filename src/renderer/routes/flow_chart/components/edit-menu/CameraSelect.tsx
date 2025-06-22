/*
 * Copyright (c) 2024 Emasoft
 *
 * This file is part of AtlasVibe, which is based on Flojoy Studio
 * Original Copyright (c) 2023-2024 Flojoy
 *
 * SPDX-License-Identifier: MIT
 * See the LICENSE file for details.
 */

import { useHardwareStore } from "@/renderer/stores/hardware";
import { DeviceSelect, SelectProps } from "./DeviceSelect";

export const CameraSelect = (props: SelectProps) => {
  const hardware = useHardwareStore((state) => state.devices);
  const cameras = hardware?.cameras;

  return (
    <DeviceSelect
      {...props}
      devices={cameras}
      placeholder="No cameras found"
      keySelector={(cam) => cam.id.toString()}
      valueSelector={(cam) => cam.id.toString()}
      nameSelector={(cam) => cam.name}
    />
  );
};

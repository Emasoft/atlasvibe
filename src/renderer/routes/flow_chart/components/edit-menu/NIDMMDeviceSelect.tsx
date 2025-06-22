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
import { useSettingsStore } from "@/renderer/stores/settings";

export const NIDMMDeviceSelect = (props: SelectProps) => {
  const hardware = useHardwareStore((state) => state.devices);
  const dmm = hardware?.nidmmDevices.filter((d) => d.address !== "");

  const { nidmmDeviceDiscovery } = useSettingsStore((state) => state.device);
  const discoveryOn = nidmmDeviceDiscovery.value;

  return (
    <DeviceSelect
      {...props}
      devices={dmm}
      placeholder={
        discoveryOn
          ? "No NI-DMM devices found | Open NI Max and refresh"
          : "Discovery is off | See settings to enable it"
      }
      keySelector={(d) => d.name}
      valueSelector={(d) => d.address}
      nameSelector={(d) => d.name}
    />
  );
};

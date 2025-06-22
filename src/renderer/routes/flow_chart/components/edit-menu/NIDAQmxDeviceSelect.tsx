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

export const NIDAQmxDeviceSelect = (props: SelectProps) => {
  const hardware = useHardwareStore((state) => state.devices);
  const daq = hardware?.nidaqmxDevices.filter((d) => d.address !== "");

  const { niDAQmxDeviceDiscovery } = useSettingsStore((state) => state.device);
  const discoveryOn = niDAQmxDeviceDiscovery.value;

  return (
    <DeviceSelect
      {...props}
      devices={daq}
      placeholder={
        discoveryOn
          ? "No NI-DAQmx devices found | Open NI Max and refresh"
          : "Discovery is off | See settings to enable it"
      }
      keySelector={(d) => d.name}
      valueSelector={(d) => d.address}
      nameSelector={(d) => d.name}
    />
  );
};

/*
 * Copyright (c) 2024 Emasoft
 *
 * This file is part of AtlasVibe, which is based on Flojoy Studio
 * Original Copyright (c) 2023-2024 Flojoy
 *
 * SPDX-License-Identifier: MIT
 * See the LICENSE file for details.
 */

import { DeviceCard, DeviceCardProps } from "./DeviceCard";

type DeviceSectionProps = {
  title: string;
  devices?: DeviceCardProps[];
};

export const DeviceSection = ({ title, devices }: DeviceSectionProps) => {
  return (
    <div>
      <h2 className="mb-2 text-lg font-bold text-accent1">{title}</h2>
      {devices ? (
        <div className="flex flex-wrap gap-4">
          {devices.map((device) => (
            <DeviceCard {...device} key={device.name} />
          ))}
        </div>
      ) : (
        <div className="text-muted-foreground">No devices found</div>
      )}
    </div>
  );
};

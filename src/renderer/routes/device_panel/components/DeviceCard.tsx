/*
 * Copyright (c) 2024 Emasoft
 *
 * This file is part of AtlasVibe, which is based on Flojoy Studio
 * Original Copyright (c) 2023-2024 Flojoy
 *
 * SPDX-License-Identifier: MIT
 * See the LICENSE file for details.
 */

export type DeviceCardProps = {
  name: string;
  description?: string;
  manufacturer?: string | null;
  port?: string;
};

export const DeviceCard = ({
  name,
  description,
  manufacturer,
  port,
}: DeviceCardProps) => {
  return (
    <div className="w-72 rounded-md bg-secondary p-2">
      <h3 className="font-semibold text-muted-foreground">{name}</h3>
      {port && <div className="max-w-fit break-all font-semibold">{port}</div>}
      {manufacturer && (
        <div className="mt-2 text-sm text-muted-foreground">{manufacturer}</div>
      )}
      <div className="py-1" />
      <div className="text-sm text-muted-foreground">{description}</div>
    </div>
  );
};

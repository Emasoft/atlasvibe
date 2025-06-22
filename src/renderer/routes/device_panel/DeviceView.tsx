/*
 * Copyright (c) 2024 Emasoft
 *
 * This file is part of AtlasVibe, which is based on Flojoy Studio
 * Original Copyright (c) 2023-2024 Flojoy
 *
 * SPDX-License-Identifier: MIT
 * See the LICENSE file for details.
 */

import { HardwareInfo } from "./components/HardwareInfo";

const DeviceView = () => {
  return (
    <div className="px-12 py-6">
      <HardwareInfo />
    </div>
  );
};

export default DeviceView;

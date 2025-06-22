/*
 * Copyright (c) 2024 Emasoft
 *
 * This file is part of AtlasVibe, which is based on Flojoy Studio
 * Original Copyright (c) 2023-2024 Flojoy
 *
 * SPDX-License-Identifier: MIT
 * See the LICENSE file for details.
 */

import { SetupStatus } from "@/renderer/types/status";
import {
  CheckCircle,
  CircleDashed,
  CircleDotDashed,
  XCircle,
} from "lucide-react";

const SetupStep = ({
  status,
  message,
}: Omit<SetupStatus, "stage">): JSX.Element => {
  return (
    <div className="flex items-center gap-2 p-2">
      <div>
        {status === "running" && <CircleDotDashed className="animate-spin" />}
        {status === "completed" && <CheckCircle />}
        {status === "pending" && <CircleDashed />}
        {status === "error" && <XCircle />}
      </div>
      <div>{message}</div>
    </div>
  );
};

export default SetupStep;

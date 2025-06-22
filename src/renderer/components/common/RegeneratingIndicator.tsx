/*
 * Copyright (c) 2024 Emasoft
 *
 * This file is part of AtlasVibe, which is based on Flojoy Studio
 * Original Copyright (c) 2023-2024 Flojoy
 *
 * SPDX-License-Identifier: MIT
 * See the LICENSE file for details.
 */

// HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
// - Created new component for showing regenerating status on blocks
// - Shows blinking "Regenerating..." label above blocks
// - Animates with pulse effect using CSS animations
//

import React from "react";
import clsx from "clsx";
import "../BlockRegenerationStyles.css";

interface RegeneratingIndicatorProps {
  visible: boolean;
  className?: string;
}

export const RegeneratingIndicator: React.FC<RegeneratingIndicatorProps> = ({
  visible,
  className,
}) => {
  if (!visible) return null;

  return (
    <div
      className={clsx("block-regenerating-indicator", className)}
      data-testid="block-regenerating-indicator"
    >
      Regenerating...
    </div>
  );
};

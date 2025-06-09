#!/usr/bin/env tsx
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Created new component for showing regenerating status on blocks
# - Shows blinking "Regenerating..." label above blocks
# - Animates with pulse effect using CSS animations
# 

import React from "react";
import clsx from "clsx";

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
      className={clsx(
        "absolute -top-8 left-1/2 -translate-x-1/2 transform",
        "rounded-md bg-yellow-500 px-2 py-1",
        "text-xs font-semibold text-white",
        "animate-pulse shadow-md",
        className,
      )}
    >
      Regenerating...
    </div>
  );
};
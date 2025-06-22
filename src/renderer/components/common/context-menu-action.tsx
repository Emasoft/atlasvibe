/*
 * Copyright (c) 2024 Emasoft
 *
 * This file is part of AtlasVibe, which is based on Flojoy Studio
 * Original Copyright (c) 2023-2024 Flojoy
 *
 * SPDX-License-Identifier: MIT
 * See the LICENSE file for details.
 */

import { Button } from "@/renderer/components/ui/button";
import { LucideIcon } from "lucide-react";

type ContextMenuActionProps = {
  onClick: () => void;
  children: React.ReactNode;
  icon: LucideIcon;
  testId: string;
};

export const ContextMenuAction = ({
  onClick,
  children,
  icon,
  testId,
}: ContextMenuActionProps) => {
  const Icon = icon;
  return (
    <Button
      onClick={onClick}
      variant="ghost"
      data-testid={testId}
      size="sm"
      className="flex w-full justify-start gap-2"
    >
      <Icon size={14} />
      {children}
    </Button>
  );
};

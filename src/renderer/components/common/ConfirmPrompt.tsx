/*
 * Copyright (c) 2024 Emasoft
 *
 * This file is part of AtlasVibe, which is based on Flojoy Studio
 * Original Copyright (c) 2023-2024 Flojoy
 *
 * SPDX-License-Identifier: MIT
 * See the LICENSE file for details.
 */

import React from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/renderer/components/ui/dialog";
import { Button } from "@/renderer/components/ui/button";

type ConfirmPromptProps = {
  open: boolean;
  handleOpenChange: (open: boolean) => void;
  handleConfirm: () => void;
  title?: string;
  description: string;
  confirmBtnText: string;
};
const ConfirmPrompt = ({
  open,
  handleOpenChange,
  handleConfirm,
  confirmBtnText,
  title,
  description,
}: ConfirmPromptProps) => {
  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>{title ?? "Are you sure?"}</DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" onClick={() => handleOpenChange(false)}>
            Cancel
          </Button>
          <Button variant="destructive" onClick={handleConfirm}>
            {confirmBtnText}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default ConfirmPrompt;

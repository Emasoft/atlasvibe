/*
 * Copyright (c) 2024 Emasoft
 *
 * This file is part of AtlasVibe, which is based on Flojoy Studio
 * Original Copyright (c) 2023-2024 Flojoy
 *
 * SPDX-License-Identifier: MIT
 * See the LICENSE file for details.
 */

import { Dialog, DialogContent } from "@/renderer/components/ui/dialog";
import {
  CONDITIONALS,
  ConditionalComponent,
} from "@/renderer/types/test-sequencer";
import { Button } from "@/renderer/components/ui/button";
import { Dispatch, SetStateAction } from "react";

export const AddConditionalModal = ({
  isConditionalModalOpen,
  handleAddConditionalModalOpen,
  handleAdd,
}: {
  isConditionalModalOpen: boolean;
  handleAddConditionalModalOpen: Dispatch<SetStateAction<boolean>>;
  handleAdd: (type: ConditionalComponent) => void;
}) => {
  return (
    <Dialog
      open={isConditionalModalOpen}
      onOpenChange={handleAddConditionalModalOpen}
    >
      <DialogContent>
        {CONDITIONALS.map((type) => {
          return <Button onClick={() => handleAdd(type)}>{type}</Button>;
        })}
      </DialogContent>
    </Dialog>
  );
};

/*
 * Copyright (c) 2024 Emasoft
 *
 * This file is part of AtlasVibe, which is based on Flojoy Studio
 * Original Copyright (c) 2023-2024 Flojoy
 *
 * SPDX-License-Identifier: MIT
 * See the LICENSE file for details.
 */

import useKeyboardShortcut from "@/renderer/hooks/useKeyboardShortcut";
import { useSave } from "./components/control-bar/SaveButton";
import { useImportSequences } from "@/renderer/hooks/useTestSequencerProject";

const SequencerKeyboardShortcuts = () => {
  const save = useSave();
  const importSequence = useImportSequences();

  useKeyboardShortcut("ctrl", "s", save);
  useKeyboardShortcut("meta", "s", save);

  useKeyboardShortcut("ctrl", "o", importSequence);
  useKeyboardShortcut("meta", "o", importSequence);

  return <div></div>;
};

export default SequencerKeyboardShortcuts;

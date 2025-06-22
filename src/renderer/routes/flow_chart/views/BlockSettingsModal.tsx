/*
 * Copyright (c) 2024 Emasoft
 *
 * This file is part of AtlasVibe, which is based on Flojoy Studio
 * Original Copyright (c) 2023-2024 Flojoy
 *
 * SPDX-License-Identifier: MIT
 * See the LICENSE file for details.
 */

import { SettingsModal } from "./SettingsModal";
import { useSettingsStore } from "@/renderer/stores/settings";

type Props = {
  isBlockSettingsOpen: boolean;
  setIsBlockSettingsOpen: (val: boolean) => void;
};

export const BlockSettingsModal = ({
  isBlockSettingsOpen,
  setIsBlockSettingsOpen,
}: Props) => {
  const { backendSettings, updateBackendSettings } = useSettingsStore(
    (state) => ({
      backendSettings: state.backend,
      updateBackendSettings: state.updateBackendSettings,
    }),
  );

  return (
    <SettingsModal
      isSettingsModalOpen={isBlockSettingsOpen}
      handleSettingsModalOpen={setIsBlockSettingsOpen}
      settings={backendSettings}
      updateSettings={updateBackendSettings}
      title="Runtime Settings"
      description="Applies when the flowchart is running."
    />
  );
};

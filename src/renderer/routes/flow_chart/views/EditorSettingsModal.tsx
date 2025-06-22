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
  isEditorSettingsOpen: boolean;
  setIsEditorSettingsOpen: (val: boolean) => void;
};

export const EditorSettingsModal = ({
  isEditorSettingsOpen,
  setIsEditorSettingsOpen,
}: Props) => {
  const { settings, updateSettings } = useSettingsStore((state) => ({
    settings: state.frontend,
    updateSettings: state.updateFrontendSettings,
  }));

  return (
    <SettingsModal
      isSettingsModalOpen={isEditorSettingsOpen}
      handleSettingsModalOpen={setIsEditorSettingsOpen}
      settings={settings}
      updateSettings={updateSettings}
      title="Editor Settings"
      description="Applies to the Atlasvibe editor"
    />
  );
};

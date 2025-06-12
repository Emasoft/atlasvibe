// Copyright (c) 2024 Emasoft (for atlasvibe modifications and derivative work)
// Copyright (c) 2024 Atlasvibe (for the original "Atlasvibe Studio" software)
//
// This software is licensed under the MIT License.
// Refer to the LICENSE file for more details.

export enum Selectors {
  addBlockBtn = "add-block-button",
  sidebarInput = "sidebar-input",
  sidebarExpandBtn = "sidebar-expand-btn",
  sidebarCloseBtn = "sidebar-close",
  blockEditToggleBtn = "toggle-edit-mode",
  deleteBlockBtn = "delete-node-button",
  closeWelcomeModalBtn = "close-welcome-modal",
  clearCanvasBtn = "clear-canvas-button",
  clearCanvasConfirmBtn = "confirm-clear-canvas",
  playBtn = "btn-play",
  cancelPlayBtn = "btn-cancel",
  settingsBtn = "settings-btn",
  keyboardShortcutBtn = "btn-keyboardshortcut",
  commandInput = "command-input",
  blockInfoBtn = "block-info-btn",
  blockEditParam = "block-edit-modal-params",
  blockInfoJson = "block-info-json",
  blockLabelEditBtn = "block-label-edit",
  blockLabelSubmit = "block-label-submit",
  blockLabelInput = "block-label-input",
  fileBtn = "file-button",
  loadAppBtn = "load-app-btn",
  appGalleryBtn = "app-gallery-btn",
  saveBtn = "btn-save",
  blockContextMenuDiv = "block-context-menu",
  contextEditBlockBtn = "context-edit-block",
  contextDuplicateBlockBtn = "context-duplicate-block",
  contextBlockInfoBtn = "context-block-info",
  contextDeleteBlockBtn = "context-delete-block",
  blockEditMenuCloseBtn = "block-edit-close-button",
  envModalBtn = "env-var-modal-button",
  envVarKeyInput = "env-var-key-input",
  envVarValueInput = "env-var-value-input",
  envVarSubmitBtn = "env-var-submit-btn",
  customBlocksTabBtn = "custom-blocks-tab",
  importCustomBlockBtn = "import-custom-block",
  depManagerModalBtn = "dep-manager-modal-button",
  testSequencerTabBtn = "test-sequencer-btn",
  addNewTestBtn = "add-new-test",
  pytestBtn = "pytest-btn",
  newDropdown = "new-dropdown", // Used for "File -> New Project"
  importTestBtn = "import-test-button",
  openSequenceGalleryBtn = "seq-gallery-btn",
  globalStatusBadge = "global-status-badge",
  newSeqModalNameInput = "new-seq-modal-name-input",
  newSeqModalDescInput = "new-seq-modal-desc-input",
  newSeqModalCreateButton = "new-seq-modal-create-btn",
  pathInputSelectButton = "path-input-select-button",
  runBtn = "run-test-btn",
  
  // Status indicators
  projectStatusIndicator = "project-status-indicator",
  blockRegeneratingIndicator = "block-regenerating-indicator",
  executionStatus = "execution-status",
  
  // Blueprint management
  blueprintManagerBtn = "blueprint-manager-btn",
  saveAsBlueprintBtn = "save-as-blueprint-btn",
  blueprintBadge = "blueprint-badge",
  blueprintItem = "blueprint-item",
  renameButton = "rename-button",

  // Selectors for project creation and general UI, used by utils.ts and block operation tests
  projectNewProjectButton = "project-new-project-button", // A more specific ID for a direct "New Project" button
  projectProjectNameInput = "project-name-input", // data-testid for project name input in modal
  projectCreateProjectModalButton = "project-create-modal-button", // data-testid for create button in new project modal

  // Selectors for block operations tests
  appWelcomeMessage = "h1[data-testid='welcome-message']", // Example, adjust if needed
  appTitle = "div[data-testid='app-title']", // Example, adjust if needed
  flowchartCanvas = "div[data-testid='flowchart-canvas']",
  propertiesPanel = "div[data-testid='properties-panel']",
  propertiesPanelBlockNameInput = "input[data-testid='prop-block-name-input']",
  // propertiesPanelUpdateNameButton = "button[data-testid='prop-update-name-button']", // If an explicit save/update button exists for name change
  modalConfirmButton = "button[data-testid='modal-confirm-button']", // General modal confirm
  modalCancelButton = "button[data-testid='modal-cancel-button']", // General modal cancel
  modalDialogTitle = "h2[data-testid='dialog-title']", // General modal title
}

// Dynamic selectors for block palette and flowchart nodes
export const blockPaletteSelectors = {
  blockByTestId: (key: string) => `div[data-testid='palette-block-${key}']`,
};

export const flowchartSelectors = {
  nodeByName: (name: string) => `div[data-testid='node'][data-node-name='${name}']`,
  nodeLabelByName: (name: string) => `div[data-testid='node-label'][data-node-name='${name}']`,
};

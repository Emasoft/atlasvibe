# Playwright Test Requirements Documentation

This document outlines the comprehensive Playwright tests created following TDD methodology. These tests define the expected behavior for UI features that need to be implemented.

## Test Files Created

### 1. `20_block_regeneration_indicators.spec.ts`

**Purpose**: Tests visual feedback during block code regeneration

**Key Requirements**:
- **Blinking Indicator**: A `.block-regenerating-indicator` element should appear above blocks during regeneration with:
  - Text: "Regenerating..."
  - CSS animation: `blink`
  - Automatically disappears when regeneration completes

- **Workflow Pause**: During regeneration:
  - Execution status shows "Paused - Block Regenerating"
  - Play button becomes disabled
  - Execution resumes automatically after regeneration

- **Header Color Change**: Block headers should:
  - Change border color to orange (rgb(250-255, xxx, 0)) during regeneration
  - Have a `pulse` animation
  - Return to original color after completion

- **Actual Regeneration**: The system must:
  - Update Python files when code is edited
  - Generate/update `block_data.json` from docstrings
  - Generate/update manifest files
  - Reflect parameter changes in the UI

### 2. `21_blueprint_management.spec.ts`

**Purpose**: Tests blueprint creation and management functionality

**Key Requirements**:
- **Save as Blueprint**: 
  - Right-click context menu option "Save as Blueprint"
  - Dialog for entering blueprint name
  - Blueprint appears in global palette with `.blueprint-badge`

- **Name Validation**:
  - Only letters (A-Z, a-z) and underscores allowed
  - Must start with a letter
  - Cannot be empty
  - Real-time validation with error messages

- **Name Collision Detection**:
  - Warning when blueprint name already exists
  - Option to overwrite or cancel
  - Clear user messaging

- **Space Replacement**:
  - First click: Preview cleaned name (spaces → underscores)
  - Leading/trailing spaces removed
  - Multiple spaces collapsed to single underscore
  - Second click: Actually save with cleaned name

- **Blueprint Renaming**:
  - Blueprint manager dialog accessible via `blueprintManagerBtn`
  - Rename button for each blueprint
  - Same validation rules apply
  - Two-step confirmation for name changes

### 3. `22_project_save_status.spec.ts`

**Purpose**: Tests project saving and status indicators

**Key Requirements**:
- **Status Indicator** (`.project-status-indicator`):
  - States: "Saved", "Unsaved changes", "Saving", "Autosaving"
  - Colors must be readable on black background:
    - Saved: Green (rgb(100-200, 200-255, 100-200))
    - Unsaved: Yellow/Amber (rgb(220+, 150-220, 0-100))
    - Saving: Light Yellow (rgb(220+, 180-240, 50-150))
    - Autosaving: Pale Yellow (rgb(220+, 200-255, 100-200))
  - Minimum luminance: 0.3 for contrast

- **Save to Any Folder**:
  - Custom save dialog with folder browser
  - Project name validation (same rules as blocks)
  - Creates project directory structure
  - Updates status with project name

- **Project Name Validation**:
  - Same rules as block names
  - Space replacement with preview
  - Collision detection for existing projects

- **Autosave System**:
  - Triggers after 2 seconds of inactivity
  - Transaction queue for rapid changes
  - Transaction log for crash recovery
  - All changes persisted even if app crashes

## Implementation Checklist

### Frontend Components Needed

1. **Block Regeneration UI**:
   - [ ] Add regenerating indicator component
   - [ ] Implement blink animation in CSS
   - [ ] Add border color states to block components
   - [ ] Add pulse animation for regenerating state
   - [ ] Hook into WebSocket for regeneration events

2. **Execution Status**:
   - [ ] Add execution status component
   - [ ] Implement pause logic during regeneration
   - [ ] Disable play button when regenerating
   - [ ] Auto-resume after regeneration

3. **Blueprint Management**:
   - [ ] Add "Save as Blueprint" to context menu
   - [ ] Create blueprint name dialog
   - [ ] Add blueprint badge component
   - [ ] Create blueprint manager dialog
   - [ ] Implement rename functionality

4. **Name Validation**:
   - [ ] Create reusable name validator
   - [ ] Pattern: `/^[A-Za-z][A-Za-z_]*$/`
   - [ ] Space cleaning function
   - [ ] Two-step preview system

5. **Project Status**:
   - [ ] Create status indicator component
   - [ ] Define color scheme for states
   - [ ] Position in header or status bar
   - [ ] Connect to project store

6. **Save Dialog**:
   - [ ] Custom save dialog component
   - [ ] Folder browser integration
   - [ ] Name validation integration
   - [ ] Collision detection

7. **Autosave**:
   - [ ] Implement debounced autosave
   - [ ] Transaction queue system
   - [ ] Transaction log for recovery
   - [ ] Background save worker

### Backend Requirements

1. **Block Regeneration**:
   - [ ] WebSocket events for regeneration status
   - [ ] Metadata generation on code change
   - [ ] Manifest update endpoints

2. **Blueprint Management**:
   - [ ] Blueprint save endpoint
   - [ ] Blueprint rename endpoint
   - [ ] Blueprint list endpoint

3. **Autosave**:
   - [ ] Transaction log system
   - [ ] Incremental save support
   - [ ] Crash recovery mechanism

### CSS Classes & Animations

```css
/* Blinking indicator */
.block-regenerating-indicator {
  animation: blink 1s ease-in-out infinite;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

/* Pulse animation for block border */
.block-regenerating {
  border-color: rgb(255, 165, 0);
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { border-width: 2px; }
  50% { border-width: 4px; }
}

/* Status colors */
.status-saved { color: rgb(150, 230, 150); }
.status-unsaved { color: rgb(240, 200, 50); }
.status-saving { color: rgb(240, 210, 100); }
.status-autosaving { color: rgb(240, 230, 150); }
```

## Testing Strategy

1. Run tests in watch mode during development
2. Tests currently document expected behavior
3. As features are implemented, tests will pass
4. Use screenshots for visual documentation
5. Console logs help debug current vs expected state

## Priority Order

1. **Autosave & Status Indicators** - Data integrity is critical
2. **Block Regeneration Feedback** - User needs to know what's happening
3. **Blueprint Management** - Enables code reuse and sharing

These tests serve as both documentation and validation of the expected behavior. Following TDD, implement features to make these tests pass.
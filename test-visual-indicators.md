# Testing Visual Indicators for Block Regeneration

## Current Implementation Status

After searching through the codebase, I found that:

### 1. File Watching is Implemented ✅
- `BlocksWatcher` in `/captain/services/consumer/blocks_watcher.py` monitors changes
- When changes are detected, it broadcasts `{"type": "manifest_update"}`
- Frontend receives this in `socket-receiver.tsx` and shows toast notification

### 2. Metadata Generation is Implemented ✅
- When custom blocks are created via `copy_blueprint_to_project()`
- Manifest generation via `create_manifest()` extracts metadata from Python code
- Automatic regeneration happens when block code is updated

### 3. Visual Indicators are NOT Implemented ❌
The following visual feedback features are **missing**:
- No border color change during regeneration
- No "regenerating" label above blocks
- No blinking animation
- No visual differentiation between regenerating and normal states

## Missing Implementation

The frontend needs to:

1. **Track regeneration state** in the block store:
```typescript
interface BlockState {
  isRegenerating: boolean;
  regenerationStartTime?: number;
}
```

2. **Update DefaultBlock component** to show visual feedback:
```typescript
// In default-block.tsx
const { isRegenerating } = useBlockRegenerationStatus(data.id);

// Add regenerating class
className={clsx(
  // existing classes...
  { "border-orange-500 animate-pulse": isRegenerating }
)}

// Show regenerating label
{isRegenerating && (
  <div className="absolute -top-6 left-1/2 transform -translate-x-1/2 
                  bg-orange-500 text-white px-2 py-1 rounded text-xs 
                  animate-blink">
    Regenerating...
  </div>
)}
```

3. **Add CSS animation**:
```css
@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

.animate-blink {
  animation: blink 1s infinite;
}
```

4. **Connect WebSocket events** to trigger regeneration state:
- When `manifest_update` is received
- Set blocks to regenerating state
- Clear state when manifest fetch completes

## Test Results Summary

| Feature | Status | Description |
|---------|--------|-------------|
| Automatic metadata generation | ✅ Implemented | Metadata files are generated when custom blocks are created |
| Metadata regeneration on change | ✅ Implemented | File watcher detects changes and triggers regeneration |
| WebSocket notifications | ✅ Implemented | `manifest_update` events are broadcast and received |
| Visual border change | ❌ Not implemented | No visual indication during regeneration |
| Regenerating label | ❌ Not implemented | No label shown above blocks |
| Blinking animation | ❌ Not implemented | No animation during regeneration |

## Conclusion

The backend functionality for automatic metadata generation and regeneration is working correctly. The file watcher detects changes and broadcasts updates via WebSocket. However, the frontend visual indicators requested by the user are **not implemented**.

To fully implement this feature, the frontend needs to be updated to:
1. Track regeneration state per block
2. Apply visual styling (border color, label)
3. Add blinking animation
4. Connect to the existing WebSocket events
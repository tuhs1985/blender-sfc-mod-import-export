# Proposal

## Why

The user currently detaches faces manually to control SFC smoothing and wants to compare that method with directly exporting Blender's corner normals.

## What Changes

- Offer current behavior, direct corner normals, and split smoothing boundaries in the export file browser; current behavior remains the default.
- Serialize Blender's evaluated corner normals directly or split temporary geometry along Blender shading boundaries, without modifying the editable mesh.
- Document behavior and qualify with synthetic Blender checks and user-directed viewer testing.

## Capabilities

### New Capabilities

- `smoothing-boundary-export`: Selectable direct normals or non-destructive smoothing-boundary splitting for MOD export.

### Modified Capabilities

None.

## Impact

Blender export UI, geometry conversion, tests and user guide. OP rendering effects remain to be checked separately.

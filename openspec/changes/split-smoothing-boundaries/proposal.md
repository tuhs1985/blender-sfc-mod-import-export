# Proposal

## Why

The user currently detaches faces manually to control SFC smoothing and prefers following Blender's smoothing settings. Offer repeatable optional export preparation based on Blender shading boundaries, with an angle alternative.

## What Changes

- Add opt-in Blender-smoothing and split-by-angle choices in export options; current behavior remains the default.
- Split temporary evaluated geometry at edges exceeding the chosen angle for standard and break models, preserving the editable Blender mesh.
- Document behavior and qualify with synthetic Blender checks and user-directed viewer testing.

## Capabilities

### New Capabilities

- `smoothing-boundary-export`: Optional non-destructive preparation for MOD export based on Blender smoothing or an angle.

### Modified Capabilities

None.

## Impact

Blender export UI, geometry conversion, tests and user guide. OP rendering effects remain to be checked separately.

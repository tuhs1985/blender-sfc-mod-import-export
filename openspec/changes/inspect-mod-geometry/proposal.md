# Proposal

## Why

Container inspection alone cannot show the geometry and material relationships needed for an OP Blender importer. Evidence from the original FCA and R4 importer supports decoding a first subset of geometry records.

## What Changes

- Decode observed `MOD0`, `VTXS`, and `POLY` fields for all LODs without changing source files.
- Report counts and material references while validating record boundaries and vertex indices.
- Keep raw corner values and avoid claiming unverified coordinate, winding, or normal semantics.

## Capabilities

### New Capabilities

- `mod-geometry-inspection`: Read-only decoding of observed MOD geometry records.

### Modified Capabilities

None.

## Impact

Adds Python parsing and synthetic tests, and extends the existing inspection workflow. Blender import, export, material rendering and game asset redistribution are outside this change.

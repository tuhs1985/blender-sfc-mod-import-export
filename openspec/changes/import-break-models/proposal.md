# Proposal

## Why

OP break models contain separately moving pieces that the first importer deliberately rejects. The original FCA and two other local examples establish piece identifiers and different pivot availability.

## What Changes

- Import supported `_brk.mod` files as separate editable piece objects.
- Preserve unambiguous numbered pivot records where available, without requiring them for OP models.
- Preserve material indices, UVs, source records and point markers; reject unsupported grouping instead of silently mixing pieces.

## Capabilities

### New Capabilities

- `blender-break-import`: Import supported OP break models as separately editable pieces.

### Modified Capabilities

None.

## Impact

Extends the experimental Blender importer and its tests. Export, smoothing preparation and game validation remain future work.

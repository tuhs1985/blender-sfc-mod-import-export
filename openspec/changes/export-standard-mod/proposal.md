# Proposal

## Why

The importer enables editing, but the project needs a way to write standard MOD models and verify round trips before game use.

## What Changes

- Build a bounded binary writer and validate against original standard models.
- Add a Blender export workflow preserving LODs, materials, texture references and named points.
- Refuse unsupported edits rather than silently discard data; do not enforce a texture format.
- Verify round trips with synthetic and local fixtures before in-game testing.

## Capabilities

### New Capabilities

- `standard-mod-export`: Write supported standard MOD models and preserve their essential data.

### Modified Capabilities

None.

## Impact

Adds writer and Blender integration to the add-on. Break-model export, smoothing preparation and game parity are separate follow-up work.

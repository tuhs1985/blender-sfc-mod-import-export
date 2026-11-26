# Proposal

## Why

The importer enables editing, but the project needs a way to write standard MOD models and verify round trips before game use.

## What Changes

- Build a bounded binary writer and validate against original standard models.
- Export newly authored and imported Blender models, including LODs, materials, texture references and named points.
- Export the artist's geometry, including open meshes and topology edits, without judging its quality. Make any data that cannot yet be represented clear; do not enforce a texture format.
- Verify controlled changes using synthetic and local fixtures and MOD Viewer during development. The user may run a sample in OP after the exporter is finished; record viewer and game results separately.

## Capabilities

### New Capabilities

- `standard-mod-export`: Write supported standard MOD models and preserve their essential data.

### Modified Capabilities

None.

## Impact

Adds writer and Blender integration to the add-on. Break-model export, smoothing preparation and game parity are separate follow-up work.

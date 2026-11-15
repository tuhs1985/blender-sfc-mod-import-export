# Proposal

## Why

The FCA-specific previews demonstrated the essential geometry, marker, diffuse, and illumination workflow. A reusable Blender importer is needed to apply it to other OP MOD files.

## What Changes

- Provide a Blender add-on that imports supported standard OP MOD files with LOD meshes, materials, textures, UVs, and named point markers.
- Keep diffuse and illumination maps as separate nodes in each material; preserve material indices and original point metadata.
- Detect unsupported or malformed structures and report meaningful errors instead of silently producing incorrect data.
- Treat break-model splitting, game lighting parity, and exporting as later work.

## Capabilities

### New Capabilities

- `blender-mod-import`: Import supported OP model files into an editable Blender scene.

### Modified Capabilities

None.

## Impact

Adds a Blender add-on, tests and installation instructions. Uses the existing observed MOD layout; no game assets are committed.

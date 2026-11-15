# Design

## Context

FCA previews used the existing Python parser, three LOD meshes, the user's verified +90-degree X orientation, point empties and separate material images. See `docs/mod0-investigation.md`. Other variants and break partitioning need further validation.

## Goals / Non-Goals

**Goals:** A reusable, installable Blender add-on for the observed normal OP layout; preserve source metadata and surface missing textures.

**Non-Goals:** Break-model piece splitting, exporter, exact OP illumination parity, or universal compatibility.

## Decisions

Separate binary parsing from Blender scene creation. Reuse the existing container and geometry parsing in a distributable add-on package; do not depend on paths outside the add-on. Parse and validate all records before scene creation. Support triangle faces initially and reject other polygon sizes explicitly, rather than silently changing triangulation. Keep stored UV values and apply FCA winding and object rotation consistently to meshes and point positions. Preserve raw point positions and material flags for future export.

Resolve explicit filenames case-insensitively alongside the MOD, or an extensionless reference to a unique Blender-supported image with the same stem. Missing, ambiguous and unreadable images produce warnings and retain names; they do not prevent geometry import. Do not impose OP texture-format restrictions on Blender assignments. Preserve material slot order including unused slots. Use separate image nodes, with an approximate diffuse-times-mask emission preview, not a claim of OP rendering parity. Build objects in a dedicated collection and clean it up if scene construction fails.

## Risks / Trade-offs

- [Different variants may not use FCA conventions] → Scope to observed structures and verify other models before claiming support.
- [Missing maps or unexpected string encodings] → Warn for missing maps and reject invalid names with useful errors.
- [Topology and normals may differ from game rendering] → Preserve raw corner records; defer definitive smoothing and export behavior.

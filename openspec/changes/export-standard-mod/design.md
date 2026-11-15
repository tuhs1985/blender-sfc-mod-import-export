# Design

## Context

The importer retains raw polygon records and material records, but does not yet preserve all source header, chunk, string and point metadata needed for export. The original FCA has three MOD0 chunks, each of which can be reconstructed byte-for-byte from the existing decoded records in a local experiment.

## Goals / Non-Goals

**Goals:** Develop a verified writer in stages, preserve unknown data and make unsupported modifications explicit.

**Non-Goals:** Break-model export, smoothing boundary modification, or claiming OP compatibility before game testing.

## Decisions

Start with pure Python bounded chunk and geometry serialization backed by synthetic and original-file round-trip checks, before creating Blender export controls. Retain original bytes for fields whose meaning is not known, including header and opaque chunk payloads; only encode fields with verified interpretations. Track transforms, LOD ordering, point names and material references through explicit source metadata. Perform validation before writing, use a temporary file plus atomic replacement, and never silently overwrite unsupported data. Do not impose image-format requirements.

For Blender authoring, the user proposes LOD objects named `fca_1`, `fca_2`, etc., exported together as `fca.mod`. Select an explicit model collection for export; a single eligible mesh without an LOD-style name is a valid one-LOD model. Reject ambiguous multi-mesh ordering and surface conflicts between names and retained IDs. Do not rename artist materials or texture images. The user reports OP searches for textures in the model directory, so present same-directory placement as practical guidance, without imposing a format restriction or silently moving files. The exact UI and handling of external images remain to be implemented and tested.

Alternatives considered: writing a file directly from scratch would require guessing unknown header fields; replaying an unchanged original would not export edits. An incremental lossless representation supports both future editing and safe preservation.

## Risks / Trade-offs

- [Normals, UV conventions and material flags remain partly unverified] → Preserve source fields and reject edits that cannot be safely encoded.
- [Original importer lacks necessary metadata] → Extend import metadata before adding the export operator.
- [Game compatibility is not proven by parsing] → Require independent OP testing after round-trip checks.

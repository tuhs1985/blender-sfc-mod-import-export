# Design

## Context

The importer retains raw polygon records and material records, but does not yet preserve all source header, chunk, string and point metadata needed for export. The original FCA has three MOD0 chunks, each of which can be reconstructed byte-for-byte from the existing decoded records in a local experiment.

## Goals / Non-Goals

**Goals:** Export standard models created in Blender or imported from MOD, preserve unknown source data where possible, and make data that cannot yet be represented explicit.

**Non-Goals:** Break-model export and smoothing boundary modification in this change. Treat viewer confirmation and actual OP testing as distinct evidence.

## Decisions

Use bounded chunk and geometry serialization backed by synthetic and original-file round-trip checks. Retain original bytes for fields whose meaning is not known when round-tripping; for new models use documented evidence-based defaults and identify unverified interpretations. Source metadata must not be required for new models. Encode edited geometry including open meshes, without assessing whether an artist's model is acceptable. Report data that cannot be encoded rather than silently claiming it was exported. Use a temporary file plus atomic replacement. Do not impose image-format requirements.

For Blender authoring, use LOD objects named `fca_1`, `fca_2`, etc., exported together as `fca.mod`; a single eligible mesh without an LOD-style name is a valid one-LOD model. Retained IDs identify imported LODs even if objects are renamed. Surface genuinely ambiguous ordering without treating ordinary mesh edits as errors. Do not rename artist materials or texture images. The original FCA and KCA files examined store texture stems without directories or extensions, and the R4 exporter strips the path and extension before writing. Derive those local stems from selected image filenames; warn if an assigned image is outside the chosen save directory because OP may not find it. Allow export after the warning; do not silently copy, move, rename or convert images, or enforce a format. Preserve unusual original references during unchanged round trips rather than silently rewriting them. Routine vertex and topology changes do not warrant warnings; reserve them for actionable problems.

Use five standard-model LODs as the user's working maximum assumption until further evidence, not as a proven OP limit or a new hard rejection. Break-piece counts are separate and have no assumed maximum; do not apply the LOD assumption to them.

Use the original Max/SFC mapping: MOD `(x,y,z)` becomes Blender `(-z,-x,y)` and Blender `(x,y,z)` becomes MOD `(-y,z,-x)`, for geometry and named points alike. Apply it consistently to imported and authored standard and break models. The user explicitly declined compatibility with the previous v0.4.0 conversion; earlier scenes may need to be reimported or realigned.

Keep imported LOD transition values, including populated values beyond the original LOD count. Initialize newly needed zero entries with D4v1ks' 100-unit baseline, extending from the preceding value where needed to avoid reversing the sequence. Authored models start at 0, 100, 200, 300, 400. The export file browser displays editable fields directly for existing LODs, prefilled with the model's values; the separate popup is reserved for existing-file overwrite choices. Exact runtime behavior remains to be verified.

Alternatives considered: writing a file directly from scratch would require guessing unknown header fields; replaying an unchanged original would not export edits. An incremental lossless representation supports both future editing and safe preservation.

## Risks / Trade-offs

- [Normals, UV conventions and material flags remain partly unverified] → Preserve source fields where possible, document assumptions, and test controlled changes in MOD Viewer.
- [Original importer lacks necessary metadata] → Extend import metadata before adding the export operator.
- [Viewer and game behavior may differ] → The user accepts MOD Viewer checks during development; record their scope and defer an optional OP sample until the exporter is finished.

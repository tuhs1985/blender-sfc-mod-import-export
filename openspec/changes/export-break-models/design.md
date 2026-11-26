# Design

Build break geometry as a single MOD0, encoding zero-based piece IDs in corner record upper words. Imported piece IDs take precedence; authored names assign their documented one-based suffix minus one. Preserve material assignments, UVs and named point empties, and convert transforms consistently with standard export. Imported source records should be preserved where feasible and any assumptions documented. Break pivots are not required for OP.

Do not impose an assumed break-piece count maximum. Many models have around five pieces, but the actual game limit is unknown; the five-LOD working assumption applies only to standard models. Binary representation limits remain separate.

Resolve output paths before writing. Ask once for existing outputs, with one checked-by-default overwrite checkbox per existing file. Unchecked existing outputs are skipped. Cancel writes nothing. Recheck destinations before replacement: do not silently replace files that were absent at confirmation or changed since confirmation. Write temporary files in their target directories and preserve source files.

Validate with synthetic data, original local break models, and Blender tests; user checks with MOD Viewer or OP. Do not assess mesh quality or impose texture formats. Respect the existing standard-only workflow.

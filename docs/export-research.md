# Standard exporter research

These observations guide the in-progress exporter; they do not establish game compatibility on their own. The original OP models used for comparison remain local.

## LOD header and ordering

The R4 exporter writes a 36-byte payload header after the `MDLS` chunk header. It writes a version-like value (`0x200`) at file offset 8, a calculated radius-like float at 12, the number of model objects at 16, a float at 20, and five more floats at 24–40. The plugin readme describes a configurable LOD tolerance and switching distances. The original FCA and KCA files have three `MOD0` chunks and a count of 3; both have `5.0` at offset 20 and `[0.0, 180.0, 350.0, 0.0, 0.0]` at offsets 24–40. FCA break has one `MOD0`, but retains the same five values. Another FCA with one `MOD0` has `[0.0, 100.0, 200.0, 300.0, 400.0]`.

These observations support, but do not by themselves prove, that offset 20 is tolerance and the following five floats are LOD distance settings. Do not infer LOD count from the number of nonzero floats. The exporter can sort mesh records by name or polygon count; preserve explicit user-selected ordering. Confirm exact meanings and game behavior with controlled exports before editing these fields.

## Materials and points

The R4 material reader loads 28-byte base records and reads eight extra bytes when flag `0x20` is set. In observed files, flag `0x01` marks a diffuse-map reference, while `0x20` accompanies the additional illumination-map reference. The importer tests `0x02` when assigning smoothing-related mesh information. Other flag meanings and the safety of modifying combinations have not been established. Current writer code can change an existing map's reference but rejects adding or removing map slots or modifying opaque material data.

Observed `PNTS` records contain three floats followed by a string-table offset. The writer can change existing positions and names, but adding or removing point records is not yet supported. Correspondence to Blender objects and game behavior still need validation.

## Geometry and texture collisions

The current binary writer preserves existing face and corner records. It supports editing UV values and existing material indices; it rejects vertex-position and vertex-index changes until normal and topology handling is verified. This is a deliberately limited binary foundation, not a complete exporter. Smoothing work remains deferred until import and export work.

An experimental Blender standard-model export operator now connects this foundation to newly imported collections carrying source metadata. It supports the tested UV, material-index, existing point and existing texture-reference changes, and refuses unsupported edits before writing. Original FCA round-trips byte-for-byte after Blender import and after saving and reopening a `.blend`; a modified FCA was exported and re-imported for selected UV, point and texture-reference checks. The operator is not a full model exporter: vertex/topology changes, added/removed points and materials, break export and exact game behavior remain unverified or unsupported. In-game validation has not been performed.

MOD texture references in the checked originals use local stems. Two distinct images such as `C:\A\hull.png` and `C:\B\hull.bmp` both encode to `hull`, so the game cannot distinguish them by the stored reference. A tested helper identifies such collisions using case-insensitive Windows paths and stems. The exporter UI still needs to expose this to the user; no collision-handling policy or texture-format restriction has been imposed yet.

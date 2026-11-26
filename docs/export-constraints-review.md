# Export constraints review — 2026-11-25

**Follow-up:** The high-priority omissions, shader-name bug, header radius, transforms/modifiers, missing UV handling and 65,536-vertex boundary described below have since been addressed in code and tested locally. The original findings are retained as review history. Interactive MOD Viewer or OP checks of the new changes and newly added LOD transition behavior remain open. String encoding, collection ambiguity and smoothing remain follow-up concerns.

Review of the current Blender add-on, including a second independent read-only review and controlled Blender 5.0.1 probes. This records implementation behavior and hypotheses; it does not establish Orion Pirates renderer behavior. Original model assets stay local.

## Collection selection follow-up — 2026-11-25

A Blender background probe created separate imported-style `fca.mod` and `fca_brk.mod` collections plus an unrelated `kca.mod` collection. Selecting an object in either FCA collection found both FCA collections and excluded KCA. Linking the selected FCA standard mesh into an additional artist collection whose name sorted first caused discovery to select that unrelated collection instead. A duplicate imported standard collection with the same source basename produced an explicit multiple-collection error. These are synthetic collection-discovery checks, not a test of every multi-scene or multi-model arrangement. Prefer the selected object's imported model collection when identifiable, while retaining pairing with the separately imported break collection; duplicate imported models still need a deliberate selection strategy.

The user chose to address this through instructions on grouping and exporter selection for now. The README describes the supported organization and the conditions to avoid; exporter behavior has not been changed.

## Closeout review — 2026-11-25

- **Empty standard meshes:** `authored_geometry` rejects evaluated meshes with no triangles, although a synthetic zero-vertex, zero-polygon MOD0 was serialized and parsed successfully by the project's binary writer. The engine and MOD Viewer behavior for that synthetic record is not established. The rejection is an add-on choice, not a demonstrated binary requirement; empty break pieces are already skipped and reported by user request. Removing this rejection also requires handling the empty vertex list in radius calculation.
- **Duplicate model numbers:** Imported meshes use numeric LOD or piece identifiers, with name-based fallback; unresolved duplicates or invalid IDs stop export. Break polygon corner records store a 16-bit piece ID, and assigning the same ID to separate pieces would make them indistinguishable. A future exporter could allocate distinct IDs for duplicates instead of requiring manual renaming, but it needs a deterministic assignment strategy. LODs are serialized in order, so the same piece-ID reasoning should not automatically be applied to LOD ordering.
- **Non-ASCII references:** The add-on currently encodes/decodes model string references as ASCII. A scan found no high-byte strings in 363 installed OP STRS chunks; this does not establish a game encoding. Keep the limitation documented until there is evidence rather than claiming OP forbids such names.
- **Unknown nested geometry chunks:** A scan of 705 geometry chunks in the installed OP models found no unknown nested records. The user closed this as a speculative concern for the current OP scope. The existing writer still rejects an unrecognized nested record if encountered rather than discard it.
- **Vertex index width:** The code supports indices 0–65535, and the observed corner record uses a 16-bit vertex index. This is a binary representation limit, not a judgment about model quality. Smoothing splits can increase the number of exported vertices.

These are research findings and suggested directions, not new OP runtime guarantees. The review did not change exporter behavior.

On 2026-11-26 the user approved allowing empty standard meshes, chose to retain unique numbering as a user naming convention, and requested clear ASCII and post-smoothing vertex-limit instructions. The exporter now serializes standard meshes with no faces, including meshes with no vertices; Blender background tests cover both zero-vertex and loose-vertex cases. Engine and MOD Viewer handling of these empty files has not been verified. Empty break pieces continue to be skipped and reported.

## High-priority data loss or incorrect metadata

- A correctly named mesh newly added to an imported model is ignored unless it also has the internal ID property. A controlled test linked `fca_4` to imported FCA: the scene contained four LOD meshes, but the exported file still contained three, without a missing-LOD warning. Independent review reproduced the equivalent issue with a new `fca_brk_99` mesh. Export discovery must honor the naming convention as well as retained IDs, and avoid silently dropping pieces.
- Material discovery looks up the literal node name `Principled BSDF`. With original FCA, renaming that shader node while leaving it connected caused the exported diffuse reference to change from `fca_1_1` to absent without a related warning. Find the relevant shader through the material graph rather than assuming a fixed node name; audit linked image detection and no-filepath images as well.
- An assigned generated or packed image without a file path is treated as no texture; an existing reference may be removed silently. A filename stem cannot be derived when none exists, but the exporter must explain that limitation rather than silently discarding the assignment.
- Editing imported vertex positions retains the original radius-like header value. A test moved a vertex to X=1000 while the header float stayed at approximately 8.47. The exact engine meaning is not confirmed, so the effect on rendering or culling is unknown. Investigate the original exporter and update applicable derived metadata when geometry changes without corrupting unchanged round trips.

## Restrictions introduced by the implementation

- Imported standard models reject adding/removing LODs with retained IDs and reject object transforms, parenting, constraints, modifiers and shape keys. The authored-mesh path already evaluates transforms and modifiers. These are implementation limitations, not established SFC rules. Support evaluated geometry while preserving correct coordinates, LOD identification, points, and normal behavior.
- Imported standard models without an active UV layer are rejected, whereas newly authored models without UVs receive zero UV coordinates. No evidence establishes that a Blender UV layer itself must exist for export. Align behavior without silently inventing texture placement.
- A new mesh with no faces is rejected; an upper vertex-count check rejects 65,536 vertices even though the encoded index is a 16-bit value. The representable index range is supported by the observed layout, but game limits and empty-model behavior remain separate questions.
- String creation encodes ASCII. The old binary uses byte strings, but the correct Windows code page and game behavior for non-ASCII names have not been established. Do not treat the current Python encoding choice as a proven format requirement.
- Renamed or extra Blender objects, duplicate matching collections, naming ambiguity, and objects belonging to multiple collections can lead to rejection, omission or selection of an unintended collection. Model selection needs clearer, predictable treatment rather than assuming the first collection or scanning unrelated collections.

## Known incomplete representation

- Imported standard-model transforms/modifiers are blocked; newly authored geometry is evaluated. Current custom normals and sharp/smooth edge settings are not encoded as artist-controlled shading. The user deliberately deferred smoothing; document the limitation and investigate after the core exporter works.
- Only a subset of Blender material graphs maps to MOD diffuse and illumination references. Some shader settings have no established MOD equivalent. Do not claim arbitrary shader nodes are preserved, and do not silently drop referenced textures.
- The writer retains several header values and uses inferred defaults for newly authored files; LOD distances, bounds and their game effects need controlled verification. The user accepts MOD Viewer as a development check and may perform a final OP sample.
- Textures are referenced by local filename stem, consistent with inspected files and the old Max exporter. Warn when textures are outside the output directory as requested; no BMP-only restriction. Same-stem image collisions can make references indistinguishable and deserve a targeted notice.

## Checks worth retaining

- Destination permission handling and explicit overwrite choices, including the existing changed-destination check; these protect files, not model quality.
- Binary bounds, required record structure, valid indices, finite numeric values, and explicit errors for data that cannot be encoded. Limits should reflect the actual representation or verified engine requirements, not aesthetic judgments about meshes.

Automated Python tests passed during this review (18 tests), but passing tests did not detect the data-loss cases above. No add-on code was changed during this review.

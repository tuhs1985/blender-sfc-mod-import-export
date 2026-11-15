# MOD0 geometry investigation

## Evidence and scope

These are observations from local model files and the R4 exporter decompilation, not a complete format specification. The observed files remain local. See `reverse-engineering.md` for the decompilation location and `remix-reference.md` for the independent runtime capture.

## Observed MOD0 layout

The R4 exporter function at `10002f90` writes two 32-bit values before a nested vertex chunk. It writes the vertex data in 12-byte records, then writes one 104-byte polygon payload per polygon, each in its own nested chunk. The helper functions write chunk tags and payload lengths and align the next chunk to four bytes. Ghidra's reconstructed argument types are not reliable enough to establish all field meanings on their own.

In 16 local normal model files, the first two little-endian values in each `MOD0` payload matched the number of 12-byte records in a following `VTXS` chunk and the number of subsequent `POLY` chunks, respectively. The matching normal and break Refit Constitution files independently produced:

| File | First count | Second count | `VTXS` bytes | `POLY` chunks | Each payload |
| --- | ---: | ---: | ---: | ---: | ---: |
| `Refit_Constitution.MOD` | 6001 | 6370 | 72012 | 6370 | 104 bytes |
| `Refit_Constitution_brk.MOD` | 6766 | 6370 | 81192 | 6370 | 104 bytes |

In these examples the nested chunks exactly fill the declared `MOD0` payload. The first count is strongly supported as a vertex-record count and the second as a polygon count; their exact interpretation in every game version remains unverified. The exporter and samples support interpreting each vertex record as three 32-bit values, but coordinate conventions and the polygon payload's fields still require direct verification.

## KCA reference

The supplied older reference folder contains `kca.mod`, `kca_brk.mod`, and five diffuse/self-illumination BMP pairs. Both models were inspected read-only:

| File | SHA-256 | Top-level chunks | Vertex records | Polygon chunks |
| --- | --- | --- | ---: | ---: |
| `kca.mod` | `0d850801ea898685f56c1a9e63c2a0cfd75b94a70ad2f981a31827e8931338dc` | `STRS`, `PNTS`, `MATS`, `MOD0` | 305 | 504 |
| `kca_brk.mod` | `9205c435ccb103685c9dbc64e93f81b5404ad63c3075e301ab401158c166dcb7` | `STRS`, `MATS`, `MOD0` | 392 | 694 |

Each `MOD0` contains one `VTXS` chunk of 12 bytes per reported vertex and the reported number of 104-byte `POLY` chunks. The normal file's `PNTS` payload is 528 bytes, consistent with 33 16-byte records; its string table includes hardpoint and damage-point names. The normal and break string tables include texture stems with corresponding `i` variants, and the folder contains matching BMP pairs. No interpretation of point-record fields or material mappings has yet been verified.

Both files have one top-level `MOD0` chunk, and the header's 32-bit value at offset 16 is `1` in both. Header float values at offsets 28 and 32 are `180.0` and `350.0`; their meanings have not been established. These numbers alone do not prove additional LOD geometry exists.

## Installed Orion Pirates FCA reference

The user supplied the FCA folder from an Orion Pirates installation. `fca.mod` (SHA-256 `a424c2a4d591c9fe3f1c2e4f0a5b3a084532e5c9fd94b548c04bc3a8995a6781`) contains `STRS`, `PNTS`, `MATS`, and **three** consecutive top-level `MOD0` chunks. The 32-bit header value at offset 16 is `3`, matching the observed geometry chunk count. The folder and string table include `fca_1_*`, `fca_2_*`, and `fca_3_*` texture stems and corresponding illumination variants.

| MOD0 | Offset | Vertex records | Polygon chunks |
| --- | ---: | ---: | ---: |
| 1 | 1580 | 205 | 376 |
| 2 | 46176 | 205 | 376 |
| 3 | 90772 | 86 | 140 |

Each chunk contains a `VTXS` payload of 12 bytes per recorded vertex and the corresponding number of 104-byte `POLY` payloads. The first two `VTXS` payloads are byte-identical. Comparing all 376 corresponding `POLY` payloads shows that only bytes 4–7 differ: each first-LOD material index is six lower than the corresponding second-LOD index. FCA's material records at those indices point to `fca_1_*` and `fca_2_*` texture stems respectively. Thus these two LODs retain the same stored vertex and polygon-corner data while using different material indices. This is an observation for this file, not a general LOD rule.

The `PNTS` payload is 464 bytes, consistent with 29 16-byte records; its string table contains hardpoint and damage-point names. For the first five records, interpreting each as three little-endian floats followed by a 32-bit string-table byte offset produces finite positions and the expected hardpoint names. The R4 importer loads the first three words as a translation and uses the fourth as a string offset. The transform from game coordinates to Blender coordinates remains to be established. Blender empties are the planned editable representation; preserve verified source data needed for export rather than assuming 3ds Max dummy objects and empties are equivalent.

## Polygon record evidence

The R4 importer at `100014c0` reads each `POLY` payload as two 32-bit values, 12 additional bytes, then a number of 28-byte corner records given by the first value. The FCA file has three corners for every polygon in all three LODs. Its 104-byte payloads therefore fit a 20-byte header plus three 28-byte records. The importer uses the second header word as the material index. Its mesh construction reads a 16-bit vertex index at the beginning of each corner record and two float values at offsets 16 and 20 of that record as texture coordinates; observed FCA indices are within their LOD's vertex count. The remaining bytes include normal-like values, but their exact semantics, the upper half of the index word, winding and coordinate transformation need further verification. Avoid hard-coding those interpretations without additional evidence.

The R4 material reader at `10001410` reads a 28-byte base record and an extra eight bytes when flag `0x20` is set. In FCA, the 32-bit values at material-record offsets 24 and 32 resolve to diffuse and illumination texture stems in `STRS` for textured records. Mapping is based on the observed sample and importer code; other flags and record fields remain unverified.

## Winding and coordinates

For every triangle in the original OP FCA's three LODs (376, 376, and 140 respectively), the cross product of the stored corner order has a negative dot product with the three floats in the polygon header interpreted as a face normal. Reversing the first two corners makes those directions agree for all 892 triangles. The R4 importer assigns triangle corner indices in the corresponding order `[1, 0, 2]`; it also assigns UV coordinates to those matching corners. This is strong FCA evidence, not yet proof for every model.

The importer's point and mesh code calls Max `RotateY` by `-pi/2` and `RotateX` by `+pi/2` (constants decoded from the original R4 binary). The precise equivalent Blender transform depends on Max's matrix conventions and multiplication order, which have not yet been verified. Do not copy these rotations directly into Blender on assumption alone.

A local Blender 5.0.1 experiment generated `output/fca-geometry-preview.blend` from the installed FCA. It retains raw MOD coordinates and UV values, reverses triangle winding, and contains three geometry objects; only the first is initially visible. Blender reported all 892 generated face normals aligned with the stored face-normal values. This checks the constructed mesh and winding, not native OP orientation, custom corner normals, appearance, or in-game parity. It has no materials, textures, hardpoints, damage points, or break pieces and is not an add-on. The generated game-derived preview stays ignored by Git.

The user confirmed that the separate `output/fca-geometry-preview-x90.blend` preview, with all three objects rotated +90 degrees around Blender's X axis, is correctly oriented. This confirms the visual orientation of this FCA preview; it does not by itself establish a universal coordinate convention or validate a complete export round trip. Apply the same object-space rotation to associated point markers in subsequent FCA previews and preserve the underlying raw data for export.

The local `output/fca-geometry-points-preview.blend` adds 29 named Blender empties from the FCA `PNTS` records. Their positions use the same +90-degree X rotation as the meshes, and each marker retains its raw coordinates and string-table offset as custom properties. Reopening the file confirmed all 29 positions match the mesh transformation. This is an experimental preview, not a complete importer or an export round-trip test; the interpretation of point types and other models remains to be verified.

The user confirmed that these markers are workable. A subsequent `output/fca-textured-preview.blend` adds 20 observed material records, assigns each polygon its stored material index, and packs the ten distinct referenced diffuse BMPs. Blender reopening confirmed all 892 faces reference packed diffuse images and all 29 empties remain. The `i` map stems are retained as material properties but are not rendered; UV appearance, illumination, color management and game parity still need visual verification. These files remain local and are not a general-purpose importer.

The user reported that the diffuse textured preview looks right. `output/fca-illumination-preview.blend` is a further local experiment: 17 applicable material records each use a separate packed illumination image node, and a preview shader multiplies diffuse color by the non-color illumination map for an emission contribution. Blender readback confirmed the 17 maps and emission connections and retained the 29 points. This is an artistic approximation for user review, not a verified reproduction of OP lighting, brightness, color-space handling or illumination blending. Original diffuse and illumination images remain separate; the experiment is not a general-purpose importer.

The user subsequently confirmed that the emission maps work in the renderer. This confirms the preview effect is visible; it does not establish exact OP lighting or brightness parity.

`fca_brk.mod` (SHA-256 `0f4c91452039c628daefd339585689f46ec5c152e55368776d8f476260bb6a4c`) has one `MOD0` with 351 vertex records and 661 polygons. Its `PNTS` payload is 112 bytes, consistent with seven 16-byte records, and `STRS` contains seven names from `fca_brk_1pivot` through `fca_brk_7pivot`. The association between those records, pivot names and geometry sections still needs decoding. These files provide an OP multi-LOD reference, not proof of behavior for every OP model.

In this break model, the upper 16 bits of each corner's first word form seven contiguous groups with IDs 0–6. All corners of each polygon agree on the ID. Their ranges are `(first polygon, count)`: `(0, 420)`, `(420, 36)`, `(456, 28)`, `(484, 48)`, `(532, 35)`, `(567, 62)`, `(629, 32)`. The R4 importer's `100024c0` uses this upper half-word when splitting contiguous geometry, supporting a piece identifier interpretation. Seven pivot records occur in the same order as the names `1pivot`–`7pivot`; mapping IDs 0–6 to those points in order is a plausible, not yet independently proven, association.

The local `output/fca-break-preview.blend` uses that provisional association to create seven separate objects with their origins at those pivot positions. Blender readback confirms seven meshes and 661 polygons. This untextured experimental preview needs a visual and game-behavior check; do not treat its pivot mapping as verified or assume other break models use identical numbering.

The user notes that pivot points are an SFC3-era feature and are not required for OP. The experimental importer therefore does not warn about absent pivot records; it preserves named points when present. FCA's records suggest OP files can contain extra information, but whether the OP engine ignores those records has not been verified. Do not infer that arbitrary extra fields or materials are safe to export.

## Material table comparison

The installed OP FCA has unused untextured entries at indices 0–2, but the local `fca_sfc1.MOD` and `fca_sfc2.MOD` each use index 1 (`misc2`) for 394 polygons and index 2 (`defrim`) for 48 polygons. Index 0 is unused in those samples. Material entries and indices must be preserved per file; the first three slots are not universally filler.

The captured F-CA Blender fixture also has 6,370 triangles, but matching counts do not prove identical input geometry or ordering. The break runtime capture reports 3,497 shared positions, distinct from the 6,766 records observed in this particular local break file; these must not be assumed to be equivalent assets or representations.

## Next investigation

Verify coordinate conversion and corner-normal behavior against controlled Blender/game comparisons. Decode the FCA LOD distances, remaining material flags and break-pivot associations. Build synthetic tests for each proven field before exposing it as an importer feature; do not apply the Remix adapter's UV conversion to MOD data without direct evidence.

## Smoothing and hard edges

The user reports that SFC does not handle smoothing groups well in their experience. Their established workaround is to detach faces at smoothing boundaries so smoothing is limited to contiguous geometry. Preserve this as an exporter design and testing concern: investigate stored corner normals, vertex sharing, Blender sharp edges and OP rendering before deciding how to represent or split boundaries. Test the user's existing workflow and any automated equivalent in OP; do not silently change mesh topology or assume smoothing-group flags alone reproduce the desired appearance.

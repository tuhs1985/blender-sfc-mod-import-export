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

`fca_brk.mod` (SHA-256 `0f4c91452039c628daefd339585689f46ec5c152e55368776d8f476260bb6a4c`) has one `MOD0` with 351 vertex records and 661 polygons. Its `PNTS` payload is 112 bytes, consistent with seven 16-byte records, and `STRS` contains seven names from `fca_brk_1pivot` through `fca_brk_7pivot`. The association between those records, pivot names and geometry sections still needs decoding. These files provide an OP multi-LOD reference, not proof of behavior for every OP model.

The captured F-CA Blender fixture also has 6,370 triangles, but matching counts do not prove identical input geometry or ordering. The break runtime capture reports 3,497 shared positions, distinct from the 6,766 records observed in this particular local break file; these must not be assumed to be equivalent assets or representations.

## Next investigation

Verify corner normals, winding and coordinate conversion against known file data and controlled Blender/game comparisons. Decode the FCA LOD distances, remaining material flags and break-pivot associations. Build synthetic tests for each proven field before exposing it as an importer feature; do not apply the Remix adapter's UV conversion to MOD data without direct evidence.

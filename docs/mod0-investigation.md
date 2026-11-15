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

The captured F-CA Blender fixture also has 6,370 triangles, but matching counts do not prove identical input geometry or ordering. The break runtime capture reports 3,497 shared positions, distinct from the 6,766 records observed in this particular local break file; these must not be assumed to be equivalent assets or representations.

## Next investigation

Trace how the importer uses `POLY` fields and verify vertex indices, corner normals, UVs, material indices and winding against known file data and the runtime fixture. Inspect materials and strings independently. Build synthetic tests for each proven field before exposing it as an importer feature; do not apply the Remix adapter's UV conversion to MOD data without direct evidence.

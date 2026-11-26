# Smoothing review: manual, Max plugins, and original OP models

## Scope and sources

This is a read-only investigation of the supplied `ModelManual.pdf`, the R3/R4 SFC plugin readmes and decompiled native plugins, and original installed OP FCA and KCA normal and break models. The manual targets SFC III; its dynamic-LOD recommendations are not automatically OP requirements. The user reports that detaching faces along smoothing boundaries is an established practical workaround for SFC.

## What the documentation says

- The R3/R4 SFC II plugin readmes describe an export prompt, **Force smoothing over the entire mesh?** They say Yes disregards Max smoothing information and smooths connected polygons together, and describe that option as intended for planets and space backdrops.
- The SFC III manual instructs users to answer No to that prompt when exporting its ship example (page 28). It does not give a complete technical specification of the No case or prove that OP handles every smoothing group correctly.
- The manual says smoothing groups may need adjustment after Boolean operations or welding, and that duplicate polygons can cause smoothing problems (pages 11–13 and 17). Its advice to weld coincident vertices is presented in the context of SFC III dynamic LOD. It should not be imposed blindly on OP: welding also removes the separated vertex boundaries that the user says they use to control smoothing.

## What the plugin actually does

The following summarizes static reverse engineering, not original source code. R4 exporter function addresses are from `output/decompiled/sfcmodexp.dle.c.txt`; the R3 exporter has corresponding routines with the same observed structure.

1. **Face normals:** R4 `10001250` calculates and normalizes a face normal from triangle vertices and writes it to the polygon record.
2. **Default, non-forced smoothing:** R4 `10002640` sorts polygons by material index, then calls `100013a0` separately for each material run. The comparator at `10001580` compares the polygon material index. Inside each run, the smoothing routine sums the face normals for each shared vertex index, divides by the number of contributing faces, and writes that average to each matching polygon corner. The average is not normalized again in this routine.
3. **Force smoothing:** The other branch calls the same averaging routine over the entire mesh's polygon range instead of one material run at a time. Shared vertex indices still determine which corners participate.
4. **Max smoothing-group information:** The exporter checks whether a Max face's smoothing-group mask is nonzero and sets a bit associated with that face's material index. The material writer uses that accumulated bit to select a material flag. The normal-averaging routine itself does not compare the face smoothing-group masks; within a material run, it uses shared vertex indices. Consequently, different Max smoothing-group numbers on faces using the same material do not, by themselves, keep the computed corner normals separate in this code path. This is distinct from saying the exporter completely ignores whether smoothing is enabled.
5. **Import into Max:** In the R4 importer mesh-building code around `10001a2b`, the material flag `0x02` selects whether a face receives a smoothing group derived from the material index; otherwise the face smoothing mask is set to zero. The shown code does not reconstruct the original per-face smoothing-group masks. It also does not visibly assign the stored per-corner normals as explicit Max normals during that mesh construction. Further Max runtime tests would be needed to establish the exact final Max appearance.

## Check against original OP model data

For the original installed OP FCA and KCA models, I independently averaged the stored polygon face-normal vectors by **(material index, vertex index)** and compared those averages with every stored corner-normal vector:

| Model | LODs | Corners matching within 0.00001 |
| --- | ---: | ---: |
| FCA normal | 3 | 2,676 / 2,676 |
| KCA normal | 3 | 3,522 / 3,522 |
| FCA break | 1 | 1,983 / 1,983 |
| KCA break | 1 | 2,082 / 2,082 |

The largest absolute component difference across the checks was approximately `1.11e-7`. This is strong evidence that these files follow the plugin's per-material/shared-vertex averaging path. It does not prove every MOD file uses that path or establish how the OP renderer handles those stored values. Some stored averages are not unit-length, consistent with the lack of a second normalization in the plugin routine.

## Implications for our exporter

The user's detach workaround has a concrete explanation in the plugin: splitting a vertex at a hard boundary prevents the adjoining faces from contributing to the same shared-vertex average, even if they use the same material. Different materials also create separate averaging runs in the observed default path. Neither conclusion establishes that material boundaries should be changed just to control shading.

For now, preserve existing corner-normal records for unchanged geometry and continue rejecting vertex/topology changes until normals can be regenerated safely. Later, evaluate an optional, non-destructive export preparation that splits vertices at explicitly marked sharp edges and/or an artist-selected angle, then computes face and corner normals. Do not alter the artist's source mesh silently; compare controlled results against the original plugin and OP before declaring equivalence. Smoothing preparation remains deferred until the basic import/export workflow works.

## Follow-up: can we preserve hard edges without manual detaching?

The `POLY` layout stores a three-float face normal and a separate three-float normal within each corner record. That retains the **resulting normal values**, not necessarily the original Max smoothing-group assignments. Different corners can reference the same vertex index and still carry different normals. This is supported by both the record layout and the original files: in FCA LOD 1, 116 of 190 referenced vertices have more than one stored corner normal when considering all materials, while no observed `(vertex, material)` pair has differing corner normals in that LOD (comparison rounded to six decimals). These differences match the old exporter's per-material averaging, but the on-disk layout itself has room for per-corner values.

A local synthetic binary experiment wrote and decoded two triangles with the same vertex index and material but different corner-normal values; the data survived byte-for-byte. Separately, Blender 5.0.1 retained distinct custom split-normal directions on the two corners of a shared vertex in a small test. These tests demonstrate representational capacity in the file layout and Blender, **not** that the OP renderer honors arbitrary different normals for shared vertices under every material flag.

There is an important lossless-round-trip detail: some original corner-normal vectors are not unit length, and the FCA's third LOD has 24 zero-length corner normals. In a controlled Blender 5.0.1 test, a custom vector `(0, 0, 0.2)` was exposed as `(0, 0, 1)` and a zero custom vector resolved to an automatically computed normal. Therefore, importing normals as Blender custom normals alone cannot preserve every original numeric value. Retain the original raw corner records separately, and reuse them for truly unchanged geometry; decide how to encode edited normals only after testing the game.

### Candidate approach after the basic exporter works

1. Import the available normal directions into Blender as corner-level custom normals for an accurate editable preview where possible, while preserving the exact original records for unchanged round trips. Handle zero vectors explicitly instead of silently claiming they were preserved as Blender normals.
2. For an edited mesh, consider writing Blender's evaluated per-corner normal directions into the MOD corner records while recomputing face normals and handling the material smooth/flat flag. Use the inverse coordinate transform correctly, including the inverse-transpose rule for non-uniform scaling. How OP applies those normals and flags is unverified.
3. Provide an optional non-destructive compatibility preparation, operating on an export copy: split shared vertices at artist-marked sharp boundaries and/or an angle threshold, while retaining geometry, UVs, materials and piece IDs. This automates the user's established workaround without modifying the editable mesh. Do not split just because a material changes unless the chosen algorithm needs it; do not silently weld intentional splits.
4. Compare a controlled shared-vertex hard-edge fixture in OP with and without the split, plus its original plugin output, before selecting a default. Include unchanged binary round trips, non-unit and zero normals, multiple materials, and break pieces in that qualification.

Until those tests, direct custom normals are a promising possibility, and automatic splitting is a compatibility fallback—not a proven replacement for the user's method. No smoothing implementation or game test was performed in this investigation.

## Blender smoothing export follow-up

The add-on now offers opt-in export preparation based on Blender shading boundaries, as well as an angle alternative. It splits temporary geometry and recalculates normals; it does not preserve exact custom normal vectors. On 2026-11-25 the user reported that a real-model test worked nicely and that smoothing was respected. The application used for the final appearance check was not specified, so this result is not recorded as a specific game or MOD Viewer test.
